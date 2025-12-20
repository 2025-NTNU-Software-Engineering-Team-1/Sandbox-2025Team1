import io
import json
import time
import docker
import pathlib
import tarfile
from typing import Dict, List, Optional

from . import config
from .utils import logger
from .meta import Sidecar
from .pipeline import fetch_problem_network_config
from .asset_cache import ensure_extracted_resource, get_asset_checksum


class NetworkController:

    def __init__(self,
                 docker_url: str,
                 submission_dir: Optional[pathlib.Path] = None):
        self.SUBMISSION_DIR = submission_dir or config.SUBMISSION_DIR
        self.resources: Dict[str, Dict] = {}

        logger().debug(
            f"(*_*)[In __init__] Initializing NetworkController with Docker URL: {docker_url}"
        )

        try:
            self.client = docker.APIClient(base_url=docker_url)
            self.docker_cli = docker.from_env(
                environment={"DOCKER_HOST": docker_url} if docker_url else None
            )
        except Exception as e:
            logger().error(f"Failed to initialize Docker client: {e}")
            self.client = None
            self.docker_cli = None

    def provision_network(self, submission_id: str, problem_id: int):
        """
        Main Entry: Fetch Config -> Check/Build Custom Image -> Setup Topology
        """
        logger().debug(
            f"(*_*)[In provision_network] Starting network provisioning for submission {submission_id}, problem {problem_id}"
        )
        if not self.client:
            raise RuntimeError("Docker client not initialized")

        # 1. Fetch Config
        logger().info(f"[{submission_id}] Fetching network config...")
        net_config = fetch_problem_network_config(problem_id)
        external_config = net_config.get("external", {})
        logger().debug(
            f"(*_*)[In provision_network] External network config: {external_config}"
        )
        sidecars_config = net_config.get("sidecars", [])
        logger().debug(
            f"(*_*)[In provision_network] Sidecars config: {sidecars_config}")
        custom_env = net_config.get("custom_env", {})
        logger().debug(
            f"(*_*)[In provision_network] Custom environment config: {custom_env}"
        )

        # 2. Handle Custom Dockerfile
        # Ensure local Docker Image is up-to-date
        custom_image_name = None
        if custom_env and custom_env.get("enabled"):
            env_whitelist = custom_env.get("env_list")
            custom_image_name = self._ensure_docker_image(
                problem_id, env_whitelist)

        # 3. Setup Network Topology
        self._setup_topology(submission_id=submission_id,
                             external_config=external_config,
                             sidecars_config=sidecars_config,
                             custom_image=custom_image_name)

    def _ensure_docker_image(
            self,
            problem_id: int,
            allowed_envs: Optional[List[str]] = None) -> List[str]:
        """
        Integrate asset_cache:
        1. Check Checksum
        2. Unzip dockerfiles.zip
        3. Build dockerfiles
        """
        logger().debug(
            f"(*_*)[In _ensure_docker_image] Checking custom docker images for problem {problem_id}"
        )
        asset_type = "network_dockerfile"
        # Check the newest Checksum
        latest_checksum = get_asset_checksum(problem_id, asset_type)
        if not latest_checksum:
            return []

        logger().info(f"Checking custom envs for problem {problem_id}...")
        extracted_path = ensure_extracted_resource(problem_id, asset_type)
        if not extracted_path:
            return []
        built_images = {}

        for item in extracted_path.iterdir():
            if item.is_dir() and (item / "Dockerfile").exists():
                folder_name = item.name
                if allowed_envs is not None and folder_name not in allowed_envs:
                    logger().info(
                        f"Skipping environment '{folder_name}' (not in env_list)."
                    )
                    continue

                # Tag：noj-custom-env:{pid}-{folder_name}
                tag = f"noj-custom-env:{problem_id}-{item.name}"
                if self._build_one_image(item, tag, latest_checksum):
                    built_images[folder_name] = tag

        return built_images

    def _build_one_image(self, context_path: pathlib.Path, tag: str,
                         checksum: str) -> bool:
        logger().debug(
            f"(*_*)[In _build_one_image] Building image {tag} with checksum {checksum}"
        )
        try:
            img = self.docker_cli.images.get(tag)
            if img.labels.get("noj_hash") == checksum:
                logger().info(f"Custom image {tag} up-to-date (hash match).")
                return True
        except docker.errors.ImageNotFound:
            pass
        except Exception as e:
            logger().warning(f"Error checking image {tag}: {e}")

        # Build Image
        logger().info(f"Building Docker image {tag}...")
        try:
            self.docker_cli.images.build(path=str(context_path),
                                         tag=tag,
                                         rm=True,
                                         labels={"noj_hash": checksum},
                                         nocache=False)
            logger().info(f"Built success: {tag}")
            return True
        except Exception as e:
            logger().error(f"Failed to build {tag}: {e}")
            return False

    def _wait_for_containers_running(self,
                                     container_ids: List[str],
                                     timeout: int = 30):
        # Check containers UP
        if not container_ids:
            return

        logger().info(f"Waiting for containers to be ready: {container_ids}")
        start_time = time.time()
        pending_ids = set(container_ids)

        while pending_ids:
            if time.time() - start_time > timeout:
                logger().warning(
                    f"Timeout waiting for containers: {pending_ids}")
                raise RuntimeError(
                    f"Network provisioning failed: Containers {pending_ids} failed to start."
                )

            current_check = list(pending_ids)
            for cid in current_check:
                try:
                    info = self.client.inspect_container(cid)
                    state = info.get("State", {})
                    status = state.get("Status", "")

                    if status == "running":
                        pending_ids.remove(cid)
                    elif status in ("exited", "dead"):
                        err = state.get("Error", "Unknown error")
                        raise RuntimeError(f"Container {cid} crashed: {err}")
                except docker.errors.NotFound:
                    pending_ids.remove(cid)
                except Exception:
                    pass

            if pending_ids:
                time.sleep(0.5)

    def _setup_topology(self,
                        submission_id: str,
                        external_config: dict,
                        sidecars_config: list,
                        custom_image: str = None):
        # Build related Sidecars and Router
        logger().debug(
            f"(*_*)[In _setup_topology] Setting up topology {external_config}")

        need_router = False
        if external_config:
            if external_config.get("ip") or external_config.get("url"):
                need_router = True

        has_sidecars = sidecars_config and len(sidecars_config) > 0
        has_custom = custom_image and len(custom_image) > 0
        need_internal = has_sidecars or has_custom

        resource_record = {
            "net_ids": [],
            "container_ids": [],
            "router_id": None,
            "mode": "none",
            "custom_image": custom_image
        }

        logger().debug(
            f"(*_*)[In _setup_topology] Setting up topology for submission {submission_id} with external_config={external_config}, sidecars_config={sidecars_config}, custom_image={custom_image}"
        )

        try:
            containers_to_wait = []
            net_name = f"noj-net-{submission_id}"

            # Cleanup existing network if any
            if need_router or need_internal:
                try:
                    logger().info(
                        f"Ensuring clean state for network: {net_name}")
                    self.client.remove_network(net_name)
                except Exception:
                    pass

            # Case 1: Mixed (Router + Sidecars)
            if need_router and need_internal:
                logger().debug(
                    f"(*_*)[In _setup_topology] Setting up mixed topology with router and sidecars for submission {submission_id}"
                )

                net_id = self.client.create_network(net_name,
                                                    driver="bridge")["Id"]
                resource_record["net_ids"].append(net_id)

                internal_ids = []

                # Start Sidecars
                if sidecars_config:
                    sc_ids = self._start_sidecars(submission_id,
                                                  sidecars_config, net_name)
                    internal_ids.extend(sc_ids)
                # Start Custom Envs
                if custom_image:
                    ce_ids = self._start_custom_envs(submission_id,
                                                     custom_image, net_name)
                    internal_ids.extend(ce_ids)

                resource_record["container_ids"].extend(internal_ids)
                containers_to_wait.extend(internal_ids)

                # Collect Sidecar IPs for Router Whitelist
                sidecar_ips = []
                for c_id in internal_ids:
                    try:
                        info = self.client.inspect_container(c_id)
                        ip = info["NetworkSettings"]["Networks"][net_name][
                            "IPAddress"]
                        if ip:
                            sidecar_ips.append(ip)
                    except Exception as e:
                        logger().warning(
                            f"Failed to inspect IP for container {c_id}: {e}")

                logger().info(f"Allowed Internal IPs: {sidecar_ips}")

                # Start Router
                router_config = external_config.copy()
                router_config["sidecar_whitelist"] = sidecar_ips

                # Router connect Bridge
                router_id = self._start_router(submission_id, router_config)

                self.client.connect_container_to_network(router_id, net_id)
                resource_record["router_id"] = router_id
                containers_to_wait.append(router_id)
                resource_record["mode"] = f"container:{router_id}"

            # Case 2: Router Only
            elif need_router:
                logger().debug(
                    f"(*_*)[In _setup_topology] Setting up router-only topology for submission {submission_id}"
                )
                router_id = self._start_router(submission_id, external_config)
                resource_record["router_id"] = router_id
                resource_record["mode"] = f"container:{router_id}"
                containers_to_wait.append(router_id)

            # Case 3: Sidecar Only
            elif need_internal:
                logger().debug(
                    f"(*_*)[In _setup_topology] Setting up sidecar-only topology for submission {submission_id}"
                )

                net_id = self.client.create_network(net_name,
                                                    driver="bridge",
                                                    internal=True)["Id"]
                resource_record["net_ids"].append(net_id)

                # Start Sidecars
                if sidecars_config:
                    sc_ids = self._start_sidecars(submission_id,
                                                  sidecars_config, net_name)
                    resource_record["container_ids"].extend(sc_ids)
                    containers_to_wait.extend(sc_ids)
                # Start Custom Envs
                if custom_image:
                    ce_ids = self._start_custom_envs(submission_id,
                                                     custom_image, net_name)
                    resource_record["container_ids"].extend(ce_ids)
                    containers_to_wait.extend(ce_ids)

                resource_record["mode"] = net_name

            self._wait_for_containers_running(containers_to_wait)
            self.resources[submission_id] = resource_record

        except Exception as e:
            logger().error(f"Topology setup failed: {e}")
            self.cleanup(submission_id, temp_resource=resource_record)
            raise e

    def _start_sidecars(self, submission_id: str, configs: list,
                        net_name: str) -> List[str]:
        ids = []
        for idx, sc in enumerate(configs):
            logger().debug(
                f"(*_*)[In _start_sidecars] Starting sidecar {idx} for submission {submission_id} with config: {sc}"
            )
            sc_obj = Sidecar(**sc)
            try:
                self.client.inspect_image(sc_obj.image)
            except docker.errors.ImageNotFound:
                logger().info(f"Pulling image {sc_obj.image}")
                self.client.pull(sc_obj.image)

            host_config = self.client.create_host_config(network_mode=net_name)
            networking_config = self.client.create_networking_config({
                net_name:
                self.client.create_endpoint_config(aliases=[sc_obj.name])
            })

            c = self.client.create_container(
                image=sc_obj.image,
                environment=sc_obj.env,
                command=sc_obj.args,
                name=f"sidecar-{submission_id}-{idx}",
                host_config=host_config,
                networking_config=networking_config,
                detach=True)
            cid = c.get("Id")
            self.client.start(cid)
            ids.append(cid)
        return ids

    def _start_custom_envs(self, submission_id: str, images_map: Dict[str,
                                                                      str],
                           net_name: str) -> List[str]:
        ids = []
        if not images_map:
            return ids

        logger().debug(
            f"(*_*)[In _start_custom_envs] Starting custom environments for submission {submission_id} with images: {images_map}"
        )
        for alias, image_tag in images_map.items():
            logger().info(
                f"Starting custom env [{alias}] using image [{image_tag}]")

            host_config = self.client.create_host_config(network_mode=net_name)
            networking_config = self.client.create_networking_config({
                net_name:
                self.client.create_endpoint_config(aliases=[alias])
            })

            try:
                c = self.client.create_container(
                    image=image_tag,
                    name=f"custom-{alias}-{submission_id}",
                    host_config=host_config,
                    networking_config=networking_config,
                    detach=True)
                cid = c.get("Id")
                self.client.start(cid)
                ids.append(cid)
            except Exception as e:
                logger().error(f"Failed to start custom env {alias}: {e}")
                raise e
        return ids

    def _start_router(self, submission_id: str, config_data: dict) -> str:
        logger().debug(
            f"(*_*)[In _start_router] Starting router for submission {submission_id} with config: {config_data}"
        )
        config_bytes = json.dumps(config_data).encode("utf-8")

        # Router default connect Bridge
        host_config = self.client.create_host_config(cap_add=["NET_ADMIN"],
                                                     network_mode="bridge")
        container = self.client.create_container(
            image="noj-router",
            name=f"router-{submission_id}",
            host_config=host_config,
            detach=True)

        # Inject config
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar_info = tarfile.TarInfo(
                name="etc/network_config/network_ip.json")
            tar_info.size = len(config_bytes)
            tar_info.mtime = time.time()
            tar.addfile(tar_info, io.BytesIO(config_bytes))
        tar_stream.seek(0)

        self.client.put_archive(container=container.get("Id"),
                                path="/",
                                data=tar_stream)
        self.client.start(container.get("Id"))
        return container.get("Id")

    def get_network_mode(self, submission_id: str) -> str:
        logger().debug(
            f"(*_*)[In get_network_mode] Getting network mode for submission {submission_id}"
        )
        res = self.resources.get(submission_id)
        if not res: return "none"
        return res.get("mode", "none")

    def get_custom_image(self, submission_id: str) -> Optional[str]:
        logger().debug(
            f"(*_*)[In get_custom_image] Getting custom image for submission {submission_id}"
        )
        res = self.resources.get(submission_id)
        if not res: return None
        return res.get("custom_image")

    def cleanup(self, submission_id: str, temp_resource: dict = None):
        logger().debug(
            f"(*_*)[In cleanup] Cleaning up resources for submission {submission_id}"
        )
        res = temp_resource or self.resources.pop(submission_id, {})

        # If Docker client is not initialized, skip cleanup operations
        if not self.client:
            logger().warning(
                f"Docker client not initialized, skipping cleanup for submission {submission_id}"
            )
            return

        c_ids = res.get("container_ids", [])[:]
        if res.get("router_id"):
            c_ids.append(res.get("router_id"))

        # Step 1: Gracefully stop containers (5 sec timeout)
        for cid in c_ids:
            try:
                self.client.stop(cid, timeout=5)
            except Exception:
                pass

        # Step 2: Force remove containers
        for cid in c_ids:
            try:
                self.client.remove_container(cid, v=True, force=True)
            except Exception:
                pass

        # Step 3: Remove networks
        for nid in res.get("net_ids", []):
            try:
                self.client.remove_network(nid)
            except Exception:
                pass
