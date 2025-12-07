import json
import time
import docker
import pathlib
import io
import tarfile
from typing import Dict, List, Optional

from . import config
from .utils import logger
from .meta import Sidecar


class NetworkController:

    def __init__(self,
                 docker_url: str,
                 submission_dir: Optional[pathlib.Path] = None):
        self.SUBMISSION_DIR = submission_dir or config.SUBMISSION_DIR
        self.sidecar_resources: Dict[str, Dict] = {}

        try:
            self.client = docker.APIClient(base_url=docker_url)
        except Exception as e:
            logger().error(
                f"Failed to initialize Docker client in NetworkController: {e}"
            )
            self.client = None

    def ensure_sidecar_images(self, sidecars: list[Sidecar]):
        """
        Check if required sidecar images exist locally; pull if missing.
        This is designed to run in a separate thread to avoid blocking.
        """
        if not self.client or not sidecars:
            logger().warning(
                "Cannot ensure sidecar images: Docker client not initialized or no sidecars provided."
            )
            return
        for sidecar in sidecars:
            try:
                self.client.inspect_image(sidecar.image)
                logger().info(
                    f"[Pre-pull] Image {sidecar.image} already exists locally."
                )
            except docker.errors.ImageNotFound:
                logger().info(
                    f"[Pre-pull] Image {sidecar.image} not found, pulling...")
                try:
                    self.client.pull(sidecar.image)
                    logger().info(
                        f"[Pre-pull] Successfully pulled {sidecar.image}")
                except Exception as e:
                    logger().error(
                        f"[Pre-pull] Failed to pull image {sidecar.image}: {e}"
                    )
            except Exception as e:
                logger().warning(
                    f"[Pre-pull] Error checking image {sidecar.image}: {e}")

    def setup_router(self, submission_id: str, config_data: dict) -> str:
        """
        Setup router container for the submission based on external_config.
        Returns the router container ID.
        """
        if not self.client:
            raise RuntimeError("Docker client not initialized")

        config_bytes = json.dumps(config_data).encode("utf-8")

        # submission_path = self.SUBMISSION_DIR / submission_id
        # network_dir = submission_path / "network_config"
        # network_dir.mkdir(parents=True, exist_ok=True)

        # conf_file = network_dir / "network_ip.json"
        # with open(conf_file, "w") as f:
        #     json.dump(config_data, f)

        logger().info(f"Starting Router for {submission_id}")

        router_img = "normal-oj/sandbox-router:latest"
        router_name = f"router-{submission_id}"
        # remove existing router container if any
        try:
            self.client.remove_container(router_name, v=True, force=True)
            logger().debug(f"Removed stale router container: {router_name}")
        except Exception:
            pass

        host_config = self.client.create_host_config(
            cap_add=["NET_ADMIN"],
            network_mode="bridge",
        )

        container = self.client.create_container(
            image=router_img,
            name=router_name,
            host_config=host_config,
            detach=True,
        )
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar_info = tarfile.TarInfo(
                name="etc/network_config/network_ip.json")
            tar_info.size = len(config_bytes)
            tar_info.mtime = time.time()
            tar.addfile(tar_info, io.BytesIO(config_bytes))
        tar_stream.seek(0)

        try:
            self.client.put_archive(
                container=container.get("Id"),
                path="/",
                data=tar_stream,
            )
        except Exception as e:
            logger().error(f"Failed to copy config to router container: {e}")
            self.client.remove_container(container.get("Id"),
                                         v=True,
                                         force=True)
            raise

        self.client.start(container)
        router_id = container.get("Id")

        res = self.sidecar_resources.get(submission_id)
        if res and res.get("network_name"):
            net_name = res["network_name"]
            try:
                self.client.connect_container_to_network(
                    container=router_id,
                    net_id=net_name,
                )
            except Exception as e:
                logger().warning(
                    f"Failed to connect router {router_id} to network {net_name}: {e}"
                )

        if not res:
            res = {}
            self.sidecar_resources[submission_id] = res
        res["router_id"] = router_id

        return router_id

    def setup_sidecars(self, submission_id: str,
                       sidecars: list[Sidecar]) -> list[str]:
        # set sidecar containers
        if not sidecars:
            return []

        if not self.client:
            raise RuntimeError("Docker client not initialized")

        logger().info(f"Setting up sidecar for Submission: {submission_id}")
        net_name = f"noj-net-{submission_id}"

        try:
            networks = self.client.networks(names=[net_name])
            for n in networks:
                nid = n.get("Id")
                if "Containers" in n and n["Containers"]:
                    for cid in n["Containers"]:
                        logger().warning(
                            f"Force removing zombie container attached to net: {cid}"
                        )
                        try:
                            self.client.remove_container(cid,
                                                         v=True,
                                                         force=True)
                        except Exception:
                            pass

                logger().warning(
                    f"Removing existing network {net_name} ({nid})")
                self.client.remove_network(nid)
        except Exception as e:
            logger().warning(
                f"Error checking/removing network {net_name}: {e}")

        for idx, sidecar in enumerate(sidecars):
            logger().debug(
                f"starting sidecar {sidecar.image} for {submission_id}")
            container_name = f"sidecar-{submission_id}-{idx}"
            try:
                self.client.remove_container(container_name,
                                             v=True,
                                             force=True)
                logger().warning(
                    f"Force removed zombie container: {container_name}")
            except Exception:
                pass

        # build internal network
        try:
            network = self.client.create_network(
                name=net_name,
                driver="bridge",
                internal=True,
                check_duplicate=True,
            )
        except Exception as e:
            logger().error(
                f"Failed to create network {net_name} for {submission_id}: {e}"
            )
            raise

        container_ids: List[str] = []

        try:
            for idx, sidecar in enumerate(sidecars):
                logger().debug(
                    f"starting sidecar {sidecar.image} for {submission_id}")

                env_list = [f"{k}={v}" for k, v in sidecar.env.items()]

                host_config = self.client.create_host_config(
                    network_mode=net_name,
                    restart_policy={"Name": "no"},
                )
                container = self.client.create_container(
                    image=sidecar.image,
                    environment=env_list,
                    command=sidecar.args,
                    name=f"sidecar-{submission_id}-{idx}",
                    host_config=host_config,
                    networking_config=self.client.create_networking_config({
                        net_name:
                        self.client.create_endpoint_config(
                            aliases=[sidecar.name])
                    }),
                )
                cid = container.get("Id")
                container_ids.append(cid)
                self.client.start(container)

            time.sleep(10)  # wait for sidecars to initialize

            self.sidecar_resources[submission_id] = {
                "network_name": net_name,
                "network_id": network.get("Id"),
                "container_ids": container_ids,
            }
            return container_ids

        except Exception as e:
            logger().error(
                f"Error setting up sidecars for {submission_id}: {e}")
            self.cleanup(
                submission_id,
                partial_ids=container_ids,
                partial_net=net_name,
            )
            raise

    def cleanup(
        self,
        submission_id: str,
        partial_ids: Optional[List[str]] = None,
        partial_net: Optional[str] = None,
    ):
        # ======= [DEBUG] =======
        print(
            f"[DEBUG] Pausing cleanup for 60s to inspect Router for submission {submission_id}..."
        )
        time.sleep(100)
        # =======================
        if not self.client:
            return
        res = self.sidecar_resources.pop(submission_id, None)

        c_ids = res.get("container_ids", []) if res else (partial_ids or [])
        net_name = res.get("network_name") if res else partial_net
        router_id = res.get("router_id") if res else None

        if router_id:
            try:
                logger().debug(f"cleaning up router container: {router_id}")
                self.client.remove_container(router_id, v=True, force=True)
            except Exception:
                pass

        for cid in c_ids:
            try:
                logger().debug(f"cleaning up sidecar container: {cid}")
                self.client.remove_container(cid, v=True, force=True)
            except Exception:
                pass

        if net_name:
            try:
                logger().debug(f"cleaning up network: {net_name}")
                self.client.remove_network(net_name)
            except Exception:
                pass

    def get_network_mode(self, submission_id: str) -> str:
        res = self.sidecar_resources.get(submission_id)
        if not res:
            return "none"
        if "router_id" in res:
            return f"container:{res['router_id']}"
        elif "network_name" in res:
            return res["network_name"]
        return "none"
