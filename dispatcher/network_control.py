import io
import json
import time
import multiprocessing
import queue
import docker
import pathlib
import tarfile
from typing import Dict, List, Optional

from . import config
from .utils import logger
from .meta import Sidecar
from .pipeline import fetch_problem_network_config
from .asset_cache import ensure_extracted_resource, get_asset_checksum


class BuildTimeoutError(Exception):
    """Exception raised when Docker build times out."""
    pass


class ImageRegistryError(Exception):
    """Exception raised when image registry is not allowed."""
    pass


def _build_image_worker(docker_url: str | None, context_path: str, tag: str,
                        checksum: str, result_queue) -> None:
    docker_cli = None
    try:
        docker_cli = docker.from_env(
            environment={"DOCKER_HOST": docker_url} if docker_url else None)
        docker_cli.images.build(
            path=context_path,
            tag=tag,
            rm=True,
            labels={"noj_hash": checksum},
            nocache=False,
        )
        result_queue.put({"ok": True})
    except Exception as exc:
        result_queue.put({"ok": False, "error": str(exc)})
    finally:
        if docker_cli:
            try:
                docker_cli.close()
            except Exception:
                pass


class NetworkController:

    def __init__(self,
                 docker_url: str,
                 submission_dir: Optional[pathlib.Path] = None,
                 cleanup_on_init: bool = True):
        self.SUBMISSION_DIR = submission_dir or config.SUBMISSION_DIR
        self.resources: Dict[str, Dict] = {}
        self.docker_url = docker_url

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

        # Cleanup stale resources from previous runs on initialization
        if cleanup_on_init and self.client:
            logger().info(
                "Performing startup cleanup of stale NOJ resources...")
            self.cleanup_stale_resources()

    def cleanup_stale_resources(self, submission_id: str = None):
        """
        Clean up any stale containers and networks left from previous runs.
        If submission_id is provided, only clean resources for that submission.
        Otherwise, clean ALL noj-related resources.

        This should be called:
        1. Before provisioning a new network (with submission_id)
        2. On startup to clean any orphaned resources (without submission_id)
        """
        if not self.client:
            logger().warning(
                "Docker client not initialized, skipping stale cleanup")
            return

        logger().info(
            f"Cleaning up stale resources (submission_id={submission_id})...")

        # Define patterns for containers and networks to clean
        if submission_id:
            container_patterns = [
                f"router-{submission_id}",
                f"sidecar-{submission_id}-",
                f"custom-*-{submission_id}",
            ]
            network_patterns = [f"noj-net-{submission_id}"]
        else:
            # Clean all NOJ-related resources
            container_patterns = ["router-", "sidecar-", "custom-"]
            network_patterns = ["noj-net-"]

        # Step 1: Find and remove stale containers
        stale_containers = []
        try:
            all_containers = self.client.containers(all=True)
            for container in all_containers:
                names = container.get("Names", [])
                for name in names:
                    # Docker names start with "/"
                    clean_name = name.lstrip("/")
                    for pattern in container_patterns:
                        if clean_name.startswith(
                                pattern) or pattern in clean_name:
                            stale_containers.append(container["Id"])
                            break
        except Exception as e:
            logger().warning(
                f"Failed to list containers for stale cleanup: {e}")

        # Remove stale containers
        for cid in stale_containers:
            try:
                logger().info(f"Removing stale container: {cid[:12]}")
                self.client.stop(cid, timeout=2)
            except Exception:
                pass  # Container may already be stopped
            try:
                self.client.remove_container(cid, v=True, force=True)
            except Exception as e:
                logger().warning(
                    f"Failed to remove stale container {cid[:12]}: {e}")

        # Step 2: Find and remove stale networks
        stale_networks = []
        try:
            all_networks = self.client.networks()
            for network in all_networks:
                name = network.get("Name", "")
                for pattern in network_patterns:
                    if name.startswith(pattern):
                        stale_networks.append(network["Id"])
                        break
        except Exception as e:
            logger().warning(f"Failed to list networks for stale cleanup: {e}")

        # Remove stale networks
        for nid in stale_networks:
            try:
                logger().info(f"Removing stale network: {nid[:12]}")
                self.client.remove_network(nid)
            except Exception as e:
                logger().warning(
                    f"Failed to remove stale network {nid[:12]}: {e}")

        if stale_containers or stale_networks:
            logger().info(
                f"Stale cleanup complete: removed {len(stale_containers)} containers, "
                f"{len(stale_networks)} networks")
        else:
            logger().debug("No stale resources found")

    def provision_network(self, submission_id: str, problem_id: int):
        """
        Main Entry: Fetch Config -> Check/Build Custom Image -> Setup Topology
        """
        logger().debug(
            f"(*_*)[In provision_network] Starting network provisioning for submission {submission_id}, problem {problem_id}"
        )
        if not self.client:
            raise RuntimeError("Docker client not initialized")

        # 0. Cleanup any stale resources from previous runs of this submission
        self.cleanup_stale_resources(submission_id)

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

        # Build Image with timeout
        timeout_seconds = config.DOCKER_BUILD_TIMEOUT
        logger().info(
            f"Building Docker image {tag} (timeout: {timeout_seconds}s)...")
        try:
            self._run_build_with_timeout(
                context_path=context_path,
                tag=tag,
                checksum=checksum,
                timeout_seconds=timeout_seconds,
            )
            logger().info(f"Built success: {tag}")
            return True
        except BuildTimeoutError as e:
            logger().error(f"Build timeout for {tag}: {e}")
            return False
        except Exception as e:
            logger().error(f"Failed to build {tag}: {e}")
            return False

    def _run_build_with_timeout(
        self,
        context_path: pathlib.Path,
        tag: str,
        checksum: str,
        timeout_seconds: int,
        worker=_build_image_worker,
        mp_context=None,
    ) -> None:
        ctx = mp_context or multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        proc = ctx.Process(
            target=worker,
            args=(self.docker_url, str(context_path), tag, checksum,
                  result_queue),
            daemon=True,
        )
        proc.start()
        proc.join(timeout_seconds)
        if proc.is_alive():
            proc.terminate()
            proc.join()
            raise BuildTimeoutError(
                f"Docker build timed out after {timeout_seconds}s")
        try:
            result = result_queue.get_nowait()
        except queue.Empty as exc:
            raise RuntimeError("Docker build exited without result") from exc
        if not result.get("ok", False):
            raise RuntimeError(result.get("error", "Unknown error"))

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
            ip_rules = external_config.get("ip", [])
            url_rules = external_config.get("url", [])
            model = external_config.get("model",
                                        "White").lower()  # Default: White

            logger().info(
                f"(*_*)[Router Decision] external_config={external_config}, "
                f"model={model}, "
                f"ip_rules={ip_rules} (len={len(ip_rules) if ip_rules else 0}), "
                f"url_rules={url_rules} (len={len(url_rules) if url_rules else 0})"
            )

            if ip_rules or url_rules:
                # Has rules: always need router to enforce them
                need_router = True
                logger().info(
                    f"(*_*)[Router Decision] need_router=True (has rules)")
            elif model == "black":
                # Black mode with empty rules: need router to allow all (open network)
                need_router = True
                logger().info(
                    f"(*_*)[Router Decision] need_router=True (black mode, allow all)"
                )
            else:
                # White mode with empty rules: no router (sandbox default blocks network)
                need_router = False
                logger().info(
                    f"(*_*)[Router Decision] need_router=False (white mode, block all)"
                )
        else:
            logger().info(
                f"(*_*)[Router Decision] need_router=False (no external_config)"
            )

        has_sidecars = sidecars_config and len(sidecars_config) > 0
        has_custom = custom_image and len(custom_image) > 0
        need_internal = has_sidecars or has_custom

        logger().info(
            f"(*_*)[Topology Decision] need_router={need_router}, "
            f"has_sidecars={has_sidecars}, has_custom={has_custom}, need_internal={need_internal}"
        )

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

                # FIX: Wait for internal containers to be running BEFORE collecting IPs
                # This fixes the race condition where IPs may be empty if collected too early
                self._wait_for_containers_running(internal_ids)

                # Collect Sidecar IPs and Names for Router Whitelist
                sidecar_ips = []
                sidecar_names = []

                # Collect names from sidecar config
                if sidecars_config:
                    for sc in sidecars_config:
                        if sc.get("name"):
                            sidecar_names.append(sc["name"])

                # Collect names from custom env config (aliases)
                if custom_image:
                    for alias in custom_image.keys():
                        sidecar_names.append(alias)

                # Collect IPs from running containers
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
                logger().info(f"Allowed Internal Names: {sidecar_names}")

                # Start Router
                router_config = external_config.copy()
                router_config["sidecar_whitelist"] = sidecar_ips
                router_config["internal_names"] = sidecar_names

                # Router connect Bridge
                router_id = self._start_router(submission_id, router_config)

                self.client.connect_container_to_network(router_id, net_id)
                resource_record["router_id"] = router_id
                # Only wait for router now (internal containers already waited above)
                containers_to_wait.append(router_id)
                resource_record["mode"] = f"container:{router_id}"
                # Wait for router entrypoint to complete firewall setup
                time.sleep(20)

            # case 2: Router
            elif need_router:
                logger().debug(
                    f"(*_*)[In _setup_topology] Setting up router-only topology for submission {submission_id}"
                )
                router_id = self._start_router(submission_id, external_config)
                resource_record["router_id"] = router_id
                resource_record["mode"] = f"container:{router_id}"
                containers_to_wait.append(router_id)
                # Wait for router entrypoint to complete firewall setup
                time.sleep(20)

            # Case 3: Sidecar Only (no router needed)
            elif need_internal:
                logger().debug(
                    f"(*_*)[In _setup_topology] Setting up sidecar-only topology for submission {submission_id}"
                )

                # Determine if network should be internal based on model
                # - Whitelist mode (white): internal=True (block external by default)
                # - Blacklist mode (black) or no model: internal=False (allow external)
                model = external_config.get(
                    "model", "black").lower() if external_config else "black"
                is_internal = (model == "white")

                logger().info(
                    f"(*_*)[Sidecar Only] model={model}, internal={is_internal}"
                )

                net_id = self.client.create_network(net_name,
                                                    driver="bridge",
                                                    internal=is_internal)["Id"]
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

            # Wait for container services (e.g., HTTP servers) to be ready
            # This delay is applied after containers are in 'running' state
            # but before student code starts executing
            if containers_to_wait and config.SERVICE_STARTUP_DELAY > 0:
                logger().info(
                    f"Waiting {config.SERVICE_STARTUP_DELAY}s for container services to be ready..."
                )
                time.sleep(config.SERVICE_STARTUP_DELAY)

            self.resources[submission_id] = resource_record

        except Exception as e:
            logger().error(f"Topology setup failed: {e}")
            self.cleanup(submission_id, temp_resource=resource_record)
            raise e

    def _validate_image_registry(self, image: str) -> bool:
        """
        Validate that the image is from an allowed registry.

        Image formats:
        - "mysql:8.0" -> docker.io (default)
        - "library/mysql:8.0" -> docker.io
        - "ghcr.io/owner/repo:tag" -> ghcr.io
        - "quay.io/owner/repo:tag" -> quay.io
        """
        allowed_registries = config.ALLOWED_REGISTRIES
        if not allowed_registries:
            return True  # If no registries configured, allow all

        # Parse the image to extract registry
        parts = image.split("/")

        if len(parts) == 1:
            # Simple image like "mysql:8.0" -> docker.io
            registry = "docker.io"
        elif len(parts) == 2:
            # Could be "library/mysql" (docker.io) or "owner/repo" (docker.io)
            # or "registry.example.com/repo" (custom registry)
            first_part = parts[0]
            if "." in first_part or ":" in first_part or first_part == "localhost":
                registry = first_part
            else:
                # Docker Hub user/repo format
                registry = "docker.io"
        else:
            # "registry.example.com/owner/repo:tag"
            registry = parts[0]

        is_allowed = registry in allowed_registries
        if not is_allowed:
            logger().warning(
                f"Image '{image}' from registry '{registry}' is not in allowed list: {allowed_registries}"
            )
        return is_allowed

    def _start_sidecars(self, submission_id: str, configs: list,
                        net_name: str) -> List[str]:
        ids = []

        for idx, sc in enumerate(configs):
            logger().debug(
                f"(*_*)[In _start_sidecars] Starting sidecar {idx} for submission {submission_id} with config: {sc}"
            )
            sc_obj = Sidecar(**sc)

            # Validate image registry
            if not self._validate_image_registry(sc_obj.image):
                raise ImageRegistryError(
                    f"Image '{sc_obj.image}' is not from an allowed registry. "
                    f"Allowed registries: {config.ALLOWED_REGISTRIES}")

            try:
                self.client.inspect_image(sc_obj.image)
            except docker.errors.ImageNotFound:
                logger().info(f"Pulling image {sc_obj.image}")
                self.client.pull(sc_obj.image)

            # Create host config with resource limits from environment
            host_config = self.client.create_host_config(
                network_mode=net_name,
                mem_limit=config.SIDECAR_MEM_LIMIT,
                cpu_period=config.SIDECAR_CPU_PERIOD,
                cpu_quota=config.SIDECAR_CPU_QUOTA,
                pids_limit=config.SIDECAR_PIDS_LIMIT,
            )
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
            logger().info(
                f"Started sidecar '{sc_obj.name}' with resource limits: "
                f"mem={config.SIDECAR_MEM_LIMIT}, cpu_quota={config.SIDECAR_CPU_QUOTA}, "
                f"pids={config.SIDECAR_PIDS_LIMIT}")
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

            # Apply same resource limits as sidecars
            host_config = self.client.create_host_config(
                network_mode=net_name,
                mem_limit=config.SIDECAR_MEM_LIMIT,
                cpu_period=config.SIDECAR_CPU_PERIOD,
                cpu_quota=config.SIDECAR_CPU_QUOTA,
                pids_limit=config.SIDECAR_PIDS_LIMIT,
            )
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
                logger().info(
                    f"Started custom env '{alias}' with resource limits: "
                    f"mem={config.SIDECAR_MEM_LIMIT}, cpu_quota={config.SIDECAR_CPU_QUOTA}, "
                    f"pids={config.SIDECAR_PIDS_LIMIT}")
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
        logger().debug(
            f"(*_*)[In _start_router] Config injected to router-{submission_id}, config: {config_data}"
        )

        self.client.start(container.get("Id"))
        logger().info(
            f"(*_*)[In _start_router] Router started: {container.get('Id')[:12]}"
        )

        return container.get("Id")

    def get_network_mode(self, submission_id: str) -> str:
        logger().debug(
            f"(*_*)[In get_network_mode] Getting network mode for submission {submission_id}"
        )
        res = self.resources.get(submission_id)
        if not res:
            logger().info(
                f"(*_*)[get_network_mode] No resources found for {submission_id}, returning 'none'"
            )
            return "none"
        mode = res.get("mode", "none")
        logger().info(
            f"(*_*)[get_network_mode] Returning mode='{mode}' for {submission_id}"
        )
        return mode

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

        net_ids = res.get("net_ids", [])
        cleanup_errors = []

        # Step 1: Disconnect containers from networks first
        # This ensures network removal won't fail due to active endpoints
        for nid in net_ids:
            for cid in c_ids:
                try:
                    self.client.disconnect_container_from_network(cid, nid)
                except Exception:
                    pass  # Container may already be disconnected

        # Step 2: Gracefully stop containers (5 sec timeout)
        for cid in c_ids:
            try:
                self.client.stop(cid, timeout=5)
            except Exception as e:
                cleanup_errors.append(f"Stop container {cid[:12]}: {e}")

        # Step 3: Force remove containers
        for cid in c_ids:
            try:
                self.client.remove_container(cid, v=True, force=True)
            except Exception as e:
                cleanup_errors.append(f"Remove container {cid[:12]}: {e}")

        # Step 4: Remove networks with retry mechanism
        for nid in net_ids:
            removed = False
            for attempt in range(3):
                try:
                    self.client.remove_network(nid)
                    removed = True
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.5)  # Wait before retry
                    else:
                        cleanup_errors.append(
                            f"Remove network {nid[:12]}: {e}")

        # Log cleanup errors if any
        if cleanup_errors:
            logger().warning(
                f"Cleanup errors for submission {submission_id}: {cleanup_errors}"
            )
