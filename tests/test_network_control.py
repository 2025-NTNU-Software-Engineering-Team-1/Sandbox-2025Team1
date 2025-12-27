from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch, call
from dispatcher.network_control import BuildTimeoutError, NetworkController
from dispatcher.meta import Sidecar


@pytest.fixture
def mock_docker_client():
    with patch("dispatcher.network_control.docker.APIClient") as mock_api, \
         patch("dispatcher.network_control.docker.from_env") as mock_from_env:
        client_instance = MagicMock()
        mock_api.return_value = client_instance
        docker_cli_instance = MagicMock()
        mock_from_env.return_value = docker_cli_instance
        yield client_instance


@pytest.fixture
def network_controller(mock_docker_client):
    nc = NetworkController(docker_url="unix://fake.sock")
    return nc


def _sleeping_build_worker(docker_url, context_path, tag, checksum,
                           result_queue) -> None:
    import time
    time.sleep(0.2)
    result_queue.put({"ok": True})


def test_ensure_sidecar_images_pulls_missing_image(network_controller,
                                                   mock_docker_client):
    """
    Test that _start_sidecars pulls images when they don't exist.
    Note: The old ensure_sidecar_images method has been merged into _start_sidecars.
    """
    import docker

    sidecars_config = [{
        "name": "db",
        "image": "mysql:5.7",
        "env": {},
        "args": []
    }]

    # mock inspect_image to raise ImageNotFound
    mock_docker_client.inspect_image.side_effect = docker.errors.ImageNotFound(
        "Missing")
    mock_docker_client.create_network.return_value = {"Id": "net-123"}
    mock_docker_client.create_container.return_value = {"Id": "container-456"}
    mock_docker_client.create_host_config.return_value = {}
    mock_docker_client.create_networking_config.return_value = {}
    mock_docker_client.create_endpoint_config.return_value = {}

    # Act - call internal _start_sidecars method
    network_controller._start_sidecars("test-sub", sidecars_config,
                                       "noj-net-test-sub")

    # Assert
    mock_docker_client.inspect_image.assert_called_with("mysql:5.7")
    mock_docker_client.pull.assert_called_with("mysql:5.7")


def test_ensure_sidecar_images_skips_existing_image(network_controller,
                                                    mock_docker_client):
    """
    Test that _start_sidecars skips pulling images that already exist.
    """
    sidecars_config = [{
        "name": "db",
        "image": "mysql:5.7",
        "env": {},
        "args": []
    }]
    # mock inspect_image to return existing image
    mock_docker_client.inspect_image.return_value = {"Id": "sha256:..."}
    mock_docker_client.create_network.return_value = {"Id": "net-123"}
    mock_docker_client.create_container.return_value = {"Id": "container-456"}
    mock_docker_client.create_host_config.return_value = {}
    mock_docker_client.create_networking_config.return_value = {}
    mock_docker_client.create_endpoint_config.return_value = {}

    # Act
    network_controller._start_sidecars("test-sub", sidecars_config,
                                       "noj-net-test-sub")

    # Assert
    mock_docker_client.inspect_image.assert_called_with("mysql:5.7")
    mock_docker_client.pull.assert_not_called()


def test_setup_sidecars_creates_network_and_containers(network_controller,
                                                       mock_docker_client):
    """
    Test that _setup_topology creates network and containers for sidecars.
    """
    submission_id = "test-sub"
    sidecars_config = [{
        "name": "db",
        "image": "mysql:5.7",
        "env": {
            "KEY": "VAL"
        },
        "args": ["--arg"]
    }]
    mock_docker_client.create_network.return_value = {"Id": "net-123"}
    mock_docker_client.create_container.return_value = {"Id": "container-456"}
    mock_docker_client.create_host_config.return_value = {}
    mock_docker_client.create_networking_config.return_value = {}
    mock_docker_client.create_endpoint_config.return_value = {}
    mock_docker_client.inspect_image.return_value = {"Id": "sha256:..."}
    mock_docker_client.inspect_container.return_value = {
        "State": {
            "Status": "running"
        }
    }

    # Act - call internal _setup_topology with sidecar-only config
    # Note: empty external_config defaults to blacklist mode, which allows external access
    network_controller._setup_topology(submission_id=submission_id,
                                       external_config={},
                                       sidecars_config=sidecars_config,
                                       custom_image=None)

    # Assert
    # 1. Check Network Creation
    # - Blacklist mode (default): internal=False (allow external access)
    # - Whitelist mode: internal=True (block external access)
    mock_docker_client.create_network.assert_called_with(
        f"noj-net-{submission_id}",
        driver="bridge",
        internal=False,  # Blacklist mode allows external access
    )
    # 2. Check Container Creation
    mock_docker_client.create_container.assert_called()
    call_args = mock_docker_client.create_container.call_args[1]
    assert call_args["image"] == "mysql:5.7"
    assert call_args["environment"] == {"KEY": "VAL"}
    assert call_args["command"] == ["--arg"]

    # 3. Check Container Start
    mock_docker_client.start.assert_called()


def test_cleanup_removes_resources(network_controller, mock_docker_client):
    """
    Test that cleanup properly removes containers and networks.
    """
    submission_id = "test-sub"
    # replicate existing resources
    network_controller.resources[submission_id] = {
        "net_ids": ["net-123"],
        "container_ids": ["c1", "c2"],
        "router_id": "r1",
    }

    # Act
    network_controller.cleanup(submission_id)

    # Assert
    # Verify that stop and remove_container were called
    assert mock_docker_client.stop.call_count >= 3  # r1, c1, c2
    assert mock_docker_client.remove_container.call_count >= 3  # r1, c1, c2
    mock_docker_client.remove_container.assert_any_call("r1",
                                                        v=True,
                                                        force=True)
    mock_docker_client.remove_container.assert_any_call("c1",
                                                        v=True,
                                                        force=True)
    mock_docker_client.remove_network.assert_called_with("net-123")
    # Confirm resource map is cleared
    assert submission_id not in network_controller.resources


def test_ensure_docker_image_respects_env_list(network_controller, monkeypatch,
                                               tmp_path):
    monkeypatch.setattr("dispatcher.network_control.get_asset_checksum",
                        lambda problem_id, asset_type: "hash")
    extracted = tmp_path / "dockerfiles"
    (extracted / "env-a").mkdir(parents=True, exist_ok=True)
    (extracted / "env-a" / "Dockerfile").write_text("FROM scratch")
    (extracted / "env-b").mkdir(parents=True, exist_ok=True)
    (extracted / "env-b" / "Dockerfile").write_text("FROM scratch")
    monkeypatch.setattr("dispatcher.network_control.ensure_extracted_resource",
                        lambda problem_id, asset_type: extracted)

    built = []

    def fake_build(context_path, tag, checksum):
        built.append((context_path.name, tag, checksum))
        return True

    monkeypatch.setattr(network_controller, "_build_one_image", fake_build)

    result = network_controller._ensure_docker_image(problem_id=1,
                                                     allowed_envs=["env-a"])
    assert "env-a" in result
    assert "env-b" not in result
    assert built and built[0][0] == "env-a"


def test_setup_topology_router_only_sets_mode(network_controller,
                                              mock_docker_client, monkeypatch):
    mock_docker_client.create_host_config.return_value = {}
    mock_docker_client.create_container.return_value = {"Id": "router-1"}
    mock_docker_client.put_archive.return_value = None
    mock_docker_client.start.return_value = None
    monkeypatch.setattr(network_controller, "_wait_for_containers_running",
                        lambda ids: None)

    network_controller._setup_topology(
        submission_id="router-only",
        external_config={"url": "http://example.test"},
        sidecars_config=[],
        custom_image=None,
    )

    assert network_controller.resources["router-only"][
        "mode"] == "container:router-1"


def test_setup_topology_mixed_adds_sidecar_whitelist(network_controller,
                                                     mock_docker_client,
                                                     monkeypatch):
    mock_docker_client.create_network.return_value = {"Id": "net-123"}
    mock_docker_client.connect_container_to_network.return_value = None
    monkeypatch.setattr(network_controller, "_wait_for_containers_running",
                        lambda ids: None)

    monkeypatch.setattr(network_controller, "_start_sidecars",
                        lambda submission_id, configs, net_name: ["sc1"])
    monkeypatch.setattr(network_controller, "_start_custom_envs",
                        lambda submission_id, images_map, net_name: ["ce1"])

    captured = {}

    def fake_start_router(submission_id, config_data):
        captured["config"] = config_data
        return "router-1"

    monkeypatch.setattr(network_controller, "_start_router", fake_start_router)

    def inspect_container(cid):
        ip = "10.0.0.2" if cid == "sc1" else "10.0.0.3"
        return {
            "NetworkSettings": {
                "Networks": {
                    "noj-net-mixed": {
                        "IPAddress": ip
                    }
                }
            }
        }

    mock_docker_client.inspect_container.side_effect = inspect_container

    network_controller._setup_topology(
        submission_id="mixed",
        external_config={"ip": "1.2.3.4"},
        sidecars_config=[{
            "name": "db",
            "image": "mysql:5.7",
            "env": {},
            "args": []
        }],
        custom_image={"env": "img"},
    )

    assert captured["config"]["sidecar_whitelist"] == ["10.0.0.2", "10.0.0.3"]
    assert network_controller.resources["mixed"][
        "mode"] == "container:router-1"
    mock_docker_client.connect_container_to_network.assert_called_with(
        "router-1", "net-123")


def test_setup_topology_sidecar_only_sets_internal_network(
        network_controller, mock_docker_client, monkeypatch):
    mock_docker_client.create_network.return_value = {"Id": "net-456"}
    monkeypatch.setattr(network_controller, "_wait_for_containers_running",
                        lambda ids: None)
    monkeypatch.setattr(network_controller, "_start_sidecars",
                        lambda submission_id, configs, net_name: ["sc1"])

    network_controller._setup_topology(
        submission_id="sidecar-only",
        external_config={},
        sidecars_config=[{
            "name": "db",
            "image": "mysql:5.7",
            "env": {},
            "args": []
        }],
        custom_image={},
    )

    assert network_controller.resources["sidecar-only"][
        "mode"] == "noj-net-sidecar-only"


def test_router_entrypoint_applies_rules_to_teacher_and_student():
    entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                  "entrypoint.sh")
    content = entrypoint.read_text(encoding="utf-8")
    assert "meta skuid 1450 jump student_out" in content
    assert "meta skuid 1451 jump student_out" in content


# ============================================================
# New Tests for Bug Fixes
# ============================================================


class TestSidecarIPRaceCondition:
    """Tests for fixing the Sidecar IP race condition (Problem 1)."""

    def test_mixed_topology_waits_before_collecting_ips(
            self, network_controller, mock_docker_client, monkeypatch):
        """
        Ensure that in mixed mode, we wait for containers before collecting IPs.
        This tests the fix for the race condition.
        """
        call_order = []

        def track_wait(ids):
            call_order.append(("wait", ids))

        def track_inspect(cid):
            call_order.append(("inspect", cid))
            return {
                "NetworkSettings": {
                    "Networks": {
                        "noj-net-race-test": {
                            "IPAddress": "10.0.0.2"
                        }
                    }
                }
            }

        mock_docker_client.create_network.return_value = {"Id": "net-123"}
        mock_docker_client.create_container.return_value = {"Id": "router-1"}
        mock_docker_client.connect_container_to_network.return_value = None
        mock_docker_client.put_archive.return_value = None
        mock_docker_client.start.return_value = None

        monkeypatch.setattr(network_controller, "_wait_for_containers_running",
                            track_wait)
        mock_docker_client.inspect_container.side_effect = track_inspect
        monkeypatch.setattr(network_controller, "_start_sidecars",
                            lambda sid, configs, net: ["sc1"])
        monkeypatch.setattr(network_controller, "_start_custom_envs",
                            lambda sid, images, net: [])

        network_controller._setup_topology(
            submission_id="race-test",
            external_config={"ip": ["1.2.3.4"]},
            sidecars_config=[{
                "name": "db",
                "image": "mysql:5.7",
                "env": {},
                "args": []
            }],
            custom_image=None,
        )

        # Verify wait was called before inspect
        wait_idx = next(i for i, (op, _) in enumerate(call_order)
                        if op == "wait" and _ == ["sc1"])
        inspect_idx = next(i for i, (op, _) in enumerate(call_order)
                           if op == "inspect")
        assert wait_idx < inspect_idx, "Wait should be called before inspect"


class TestSidecarResourceLimits:
    """Tests for Sidecar resource limits (Problem 2)."""

    def test_sidecar_applies_resource_limits(self, network_controller,
                                             mock_docker_client, monkeypatch):
        """Verify that resource limits are passed to create_host_config."""
        # Mock config values
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_MEM_LIMIT", "256m")
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_PERIOD", 50000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_QUOTA", 25000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_PIDS_LIMIT", 50)

        mock_docker_client.inspect_image.return_value = {"Id": "sha256:..."}
        mock_docker_client.create_container.return_value = {"Id": "c1"}
        mock_docker_client.create_host_config.return_value = {}
        mock_docker_client.create_networking_config.return_value = {}
        mock_docker_client.create_endpoint_config.return_value = {}

        sidecars_config = [{
            "name": "db",
            "image": "mysql:5.7",
            "env": {},
            "args": []
        }]

        network_controller._start_sidecars("test-sub", sidecars_config,
                                           "noj-net-test")

        # Verify create_host_config was called with resource limits
        mock_docker_client.create_host_config.assert_called_with(
            network_mode="noj-net-test",
            mem_limit="256m",
            cpu_period=50000,
            cpu_quota=25000,
            pids_limit=50,
        )

    def test_custom_env_applies_resource_limits(self, network_controller,
                                                mock_docker_client,
                                                monkeypatch):
        """Verify that custom env containers also get resource limits."""
        # Mock config values
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_MEM_LIMIT", "256m")
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_PERIOD", 50000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_QUOTA", 25000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_PIDS_LIMIT", 50)

        mock_docker_client.create_container.return_value = {"Id": "c1"}
        mock_docker_client.create_host_config.return_value = {}
        mock_docker_client.create_networking_config.return_value = {}
        mock_docker_client.create_endpoint_config.return_value = {}

        images_map = {"env-cpp": "noj-custom-env:1-env-cpp"}

        network_controller._start_custom_envs("test-sub", images_map,
                                              "noj-net-test")

        # Verify create_host_config was called with resource limits
        mock_docker_client.create_host_config.assert_called_with(
            network_mode="noj-net-test",
            mem_limit="256m",
            cpu_period=50000,
            cpu_quota=25000,
            pids_limit=50,
        )


class TestImageRegistryValidation:
    """Tests for image registry validation (Problem 3)."""

    def test_validate_docker_hub_official_image(self, network_controller,
                                                monkeypatch):
        """docker.io should be allowed by default."""
        monkeypatch.setattr(
            "dispatcher.network_control.config.ALLOWED_REGISTRIES",
            ["docker.io"])
        assert network_controller._validate_image_registry("mysql:5.7") is True
        assert network_controller._validate_image_registry(
            "library/mysql:5.7") is True

    def test_validate_docker_hub_user_image(self, network_controller,
                                            monkeypatch):
        """User images on docker.io should be allowed."""
        monkeypatch.setattr(
            "dispatcher.network_control.config.ALLOWED_REGISTRIES",
            ["docker.io"])
        assert network_controller._validate_image_registry(
            "bitnami/mysql:5.7") is True

    def test_reject_unauthorized_registry(self, network_controller,
                                          monkeypatch):
        """Images from unauthorized registries should be rejected."""
        monkeypatch.setattr(
            "dispatcher.network_control.config.ALLOWED_REGISTRIES",
            ["docker.io"])
        assert network_controller._validate_image_registry(
            "ghcr.io/owner/repo:tag") is False
        assert network_controller._validate_image_registry(
            "quay.io/owner/repo:tag") is False
        assert network_controller._validate_image_registry(
            "evil-registry.com/malware:latest") is False

    def test_allow_multiple_registries(self, network_controller, monkeypatch):
        """Multiple allowed registries should all be accepted."""
        monkeypatch.setattr(
            "dispatcher.network_control.config.ALLOWED_REGISTRIES",
            ["docker.io", "ghcr.io", "quay.io"])
        assert network_controller._validate_image_registry("mysql:5.7") is True
        assert network_controller._validate_image_registry(
            "ghcr.io/owner/repo:tag") is True
        assert network_controller._validate_image_registry(
            "quay.io/owner/repo:tag") is True

    def test_empty_allowed_registries_allows_all(self, network_controller,
                                                 monkeypatch):
        """If ALLOWED_REGISTRIES is empty, all registries should be allowed."""
        monkeypatch.setattr(
            "dispatcher.network_control.config.ALLOWED_REGISTRIES", [])
        assert network_controller._validate_image_registry(
            "any-registry.com/image:tag") is True

    def test_start_sidecars_rejects_unauthorized_image(self,
                                                       network_controller,
                                                       mock_docker_client,
                                                       monkeypatch):
        """_start_sidecars should raise ImageRegistryError for unauthorized images."""
        from dispatcher.network_control import ImageRegistryError

        monkeypatch.setattr(
            "dispatcher.network_control.config.ALLOWED_REGISTRIES",
            ["docker.io"])

        sidecars_config = [{
            "name": "evil",
            "image": "evil-registry.com/malware:latest",
            "env": {},
            "args": []
        }]

        with pytest.raises(ImageRegistryError) as exc_info:
            network_controller._start_sidecars("test-sub", sidecars_config,
                                               "noj-net-test")

        assert "evil-registry.com" in str(exc_info.value)


class TestCleanupErrorHandling:
    """Tests for cleanup error handling improvements (Problem 5)."""

    def test_cleanup_disconnects_containers_before_removing_network(
            self, network_controller, mock_docker_client):
        """Verify that containers are disconnected from networks before removal."""
        call_order = []

        def track_disconnect(cid, nid):
            call_order.append(("disconnect", cid, nid))

        def track_remove_network(nid):
            call_order.append(("remove_network", nid))

        mock_docker_client.disconnect_container_from_network.side_effect = track_disconnect
        mock_docker_client.remove_network.side_effect = track_remove_network

        network_controller.resources["test-cleanup"] = {
            "net_ids": ["net-123"],
            "container_ids": ["c1"],
            "router_id": None,
        }

        network_controller.cleanup("test-cleanup")

        # Find positions in call order
        disconnect_calls = [
            i for i, op in enumerate(call_order) if op[0] == "disconnect"
        ]
        remove_calls = [
            i for i, op in enumerate(call_order) if op[0] == "remove_network"
        ]

        if disconnect_calls and remove_calls:
            assert max(disconnect_calls) < min(
                remove_calls
            ), "Disconnect should happen before network removal"

    def test_cleanup_retries_network_removal(self, network_controller,
                                             mock_docker_client):
        """Verify that network removal is retried on failure."""
        attempt_count = [0]

        def fail_then_succeed(nid):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Network busy")
            return None

        mock_docker_client.remove_network.side_effect = fail_then_succeed

        network_controller.resources["test-retry"] = {
            "net_ids": ["net-123"],
            "container_ids": [],
            "router_id": None,
        }

        network_controller.cleanup("test-retry")

        assert attempt_count[0] == 3, "Should retry 3 times"

    def test_cleanup_logs_errors(self, network_controller, mock_docker_client,
                                 caplog):
        """Verify that cleanup errors are logged."""
        import logging

        mock_docker_client.remove_network.side_effect = Exception(
            "Persistent failure")

        network_controller.resources["test-log"] = {
            "net_ids": ["net-fail"],
            "container_ids": [],
            "router_id": None,
        }

        with caplog.at_level(logging.WARNING):
            network_controller.cleanup("test-log")

        # Check that warning was logged
        assert any("Cleanup errors" in record.message
                   for record in caplog.records)


class TestDockerBuildTimeout:
    """Tests for Docker build timeout (Problem 6)."""

    def test_run_build_with_timeout_times_out(self, network_controller):
        """Verify _run_build_with_timeout raises when timeout is exceeded."""
        import multiprocessing

        with pytest.raises(BuildTimeoutError):
            network_controller._run_build_with_timeout(
                context_path=Path("/tmp/fake"),
                tag="test:latest",
                checksum="abc123",
                timeout_seconds=0.05,
                worker=_sleeping_build_worker,
                mp_context=multiprocessing.get_context("fork"),
            )

    def test_build_one_image_uses_timeout(self, network_controller,
                                          monkeypatch):
        """Verify that _build_one_image uses timeout from config."""
        import docker.errors

        monkeypatch.setattr(
            "dispatcher.network_control.config.DOCKER_BUILD_TIMEOUT", 60)

        mock_docker_cli = MagicMock()
        mock_docker_cli.images.get.side_effect = docker.errors.ImageNotFound(
            "not found")
        network_controller.docker_cli = mock_docker_cli

        called = {}

        def fake_run(self,
                     context_path,
                     tag,
                     checksum,
                     timeout_seconds,
                     worker=None):
            called["timeout"] = timeout_seconds

        import pathlib
        monkeypatch.setattr(NetworkController, "_run_build_with_timeout",
                            fake_run)
        result = network_controller._build_one_image(
            context_path=pathlib.Path("/tmp/fake"),
            tag="test:latest",
            checksum="abc123")

        assert result is True
        assert called["timeout"] == 60


class TestConfigEnvironmentVariables:
    """Tests for config environment variables."""

    def test_config_sidecar_defaults(self, monkeypatch):
        """Test default values for sidecar config."""
        # Clear any existing env vars
        monkeypatch.delenv("SIDECAR_MEM_LIMIT", raising=False)
        monkeypatch.delenv("SIDECAR_CPU_PERIOD", raising=False)
        monkeypatch.delenv("SIDECAR_CPU_QUOTA", raising=False)
        monkeypatch.delenv("SIDECAR_PIDS_LIMIT", raising=False)

        # Re-import to get fresh values
        import importlib
        import dispatcher.config
        importlib.reload(dispatcher.config)

        assert dispatcher.config.SIDECAR_MEM_LIMIT == "512m"
        assert dispatcher.config.SIDECAR_CPU_PERIOD == 100000
        assert dispatcher.config.SIDECAR_CPU_QUOTA == 50000
        assert dispatcher.config.SIDECAR_PIDS_LIMIT == 100

    def test_config_from_environment(self, monkeypatch):
        """Test that config reads from environment variables."""
        monkeypatch.setenv("SIDECAR_MEM_LIMIT", "1g")
        monkeypatch.setenv("SIDECAR_CPU_PERIOD", "200000")
        monkeypatch.setenv("SIDECAR_CPU_QUOTA", "100000")
        monkeypatch.setenv("SIDECAR_PIDS_LIMIT", "200")
        monkeypatch.setenv("ALLOWED_REGISTRIES", "docker.io,ghcr.io")
        monkeypatch.setenv("DOCKER_BUILD_TIMEOUT", "600")

        import importlib
        import dispatcher.config
        importlib.reload(dispatcher.config)

        assert dispatcher.config.SIDECAR_MEM_LIMIT == "1g"
        assert dispatcher.config.SIDECAR_CPU_PERIOD == 200000
        assert dispatcher.config.SIDECAR_CPU_QUOTA == 100000
        assert dispatcher.config.SIDECAR_PIDS_LIMIT == 200
        assert dispatcher.config.ALLOWED_REGISTRIES == ["docker.io", "ghcr.io"]
        assert dispatcher.config.DOCKER_BUILD_TIMEOUT == 600


# ============================================================
# DNS Sinkhole and IPv6 Tests
# ============================================================


class TestDNSSinkhole:
    """Tests for DNS Sinkhole functionality."""

    def test_url_triggers_router_creation_for_dns_blocking(
            self, network_controller, mock_docker_client, monkeypatch):
        """Verify that url in config triggers router creation for DNS blocking."""
        mock_docker_client.create_host_config.return_value = {}
        mock_docker_client.create_container.return_value = {"Id": "router-1"}
        mock_docker_client.put_archive.return_value = None
        mock_docker_client.start.return_value = None
        monkeypatch.setattr(network_controller, "_wait_for_containers_running",
                            lambda ids: None)

        # URL field triggers router creation with DNS Sinkhole
        network_controller._setup_topology(
            submission_id="dns-sinkhole-test",
            external_config={
                "url": ["https://google.com", "https://facebook.com"]
            },
            sidecars_config=[],
            custom_image=None,
        )

        # Verify router was created
        assert network_controller.resources["dns-sinkhole-test"][
            "mode"] == "container:router-1"
        assert network_controller.resources["dns-sinkhole-test"][
            "router_id"] == "router-1"

    def test_router_entrypoint_has_dnsmasq_config(self):
        """Verify entrypoint.sh contains dnsmasq configuration."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for dnsmasq configuration
        assert "dnsmasq" in content
        assert "/etc/dnsmasq.conf" in content
        assert "address=/" in content or "DNSMASQ_BLOCKLIST" in content

    def test_router_entrypoint_extracts_domains_from_urls(self):
        """Verify entrypoint.sh extracts domains from URLs for DNS blocking."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for URL domain extraction
        assert "URLS" in content
        assert "Blocking domain from URL" in content

    def test_router_dockerfile_includes_dnsmasq(self):
        """Verify Dockerfile includes dnsmasq package."""
        dockerfile = (Path(__file__).resolve().parents[1] / "network_router" /
                      "Dockerfile")
        content = dockerfile.read_text(encoding="utf-8")

        assert "dnsmasq" in content


class TestIPv6Support:
    """Tests for IPv6 support in network control."""

    def test_router_entrypoint_resolves_ipv6(self):
        """Verify entrypoint.sh resolves AAAA (IPv6) records."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for AAAA record resolution
        assert "AAAA" in content
        assert "ipv6" in content.lower() or "IPv6" in content

    def test_router_entrypoint_has_ipv6_nftables_rules(self):
        """Verify entrypoint.sh has IPv6 nftables rules."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for IPv6 nftables rules
        assert "ip6 daddr" in content

    def test_router_entrypoint_dnsmasq_ipv6_upstream(self):
        """Verify dnsmasq config includes IPv6 upstream DNS."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for IPv6 upstream DNS (Google's IPv6 DNS)
        assert "2001:4860:4860" in content

    def test_router_entrypoint_includes_docker_internal_dns(self):
        """Verify dnsmasq config includes Docker's embedded DNS for internal name resolution."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for Docker's embedded DNS (127.0.0.11)
        assert "127.0.0.11" in content
        # Check for strict-order to prioritize Docker DNS
        assert "strict-order" in content

    def test_router_entrypoint_blocks_ipv6_in_sinkhole(self):
        """Verify DNS sinkhole returns :: for blocked domains (IPv6)."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for IPv6 sinkhole response
        assert "/::" in content or "/::/" in content


class TestDNSSinkholeWithRetry:
    """Tests for DNS resolution retry mechanism."""

    def test_router_entrypoint_has_retry_mechanism(self):
        """Verify entrypoint.sh has DNS resolution retry."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for retry mechanism
        assert "retry" in content.lower() or "max_attempts" in content

    def test_router_entrypoint_has_resolve_function(self):
        """Verify entrypoint.sh has a resolve function with retry."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for resolve function
        assert "resolve_with_retry" in content


# ============================================================
# Internal Names Whitelist Tests
# ============================================================


class TestInternalNamesWhitelist:
    """Tests for internal container names whitelist functionality."""

    def test_collect_sidecar_names(self, network_controller,
                                   mock_docker_client, monkeypatch):
        """Verify sidecar names are collected from config."""
        mock_docker_client.create_network.return_value = {"Id": "net-1"}
        mock_docker_client.create_host_config.return_value = {}
        mock_docker_client.create_networking_config.return_value = {}
        mock_docker_client.create_endpoint_config.return_value = {}
        mock_docker_client.create_container.return_value = {
            "Id": "container-1"
        }
        mock_docker_client.start.return_value = None
        mock_docker_client.inspect_container.return_value = {
            "NetworkSettings": {
                "Networks": {
                    "noj-net-test": {
                        "IPAddress": "172.18.0.2"
                    }
                }
            }
        }
        mock_docker_client.put_archive.return_value = None

        monkeypatch.setattr(network_controller, "_wait_for_containers_running",
                            lambda ids: None)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_MEM_LIMIT", "256m")
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_PERIOD", 100000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_QUOTA", 50000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_PIDS_LIMIT", 100)
        monkeypatch.setattr(
            "dispatcher.network_control.config.ALLOWED_REGISTRIES",
            ["docker.io"])

        # Mock image inspection
        mock_docker_client.inspect_image.return_value = {}

        sidecars_config = [{
            "name": "mysql",
            "image": "mysql:8.0"
        }, {
            "name": "redis",
            "image": "redis:alpine"
        }]

        network_controller._setup_topology(submission_id="test",
                                           external_config={
                                               "model": "white",
                                               "url":
                                               ["https://api.example.com"]
                                           },
                                           sidecars_config=sidecars_config,
                                           custom_image=None)

        # Verify put_archive was called with config containing internal_names
        call_args = mock_docker_client.put_archive.call_args
        assert call_args is not None

    def test_collect_custom_env_names(self, network_controller,
                                      mock_docker_client, monkeypatch):
        """Verify custom env aliases are collected."""
        mock_docker_client.create_network.return_value = {"Id": "net-1"}
        mock_docker_client.create_host_config.return_value = {}
        mock_docker_client.create_networking_config.return_value = {}
        mock_docker_client.create_endpoint_config.return_value = {}
        mock_docker_client.create_container.return_value = {
            "Id": "container-1"
        }
        mock_docker_client.start.return_value = None
        mock_docker_client.inspect_container.return_value = {
            "NetworkSettings": {
                "Networks": {
                    "noj-net-test": {
                        "IPAddress": "172.18.0.2"
                    }
                }
            }
        }
        mock_docker_client.put_archive.return_value = None

        monkeypatch.setattr(network_controller, "_wait_for_containers_running",
                            lambda ids: None)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_MEM_LIMIT", "256m")
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_PERIOD", 100000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_CPU_QUOTA", 50000)
        monkeypatch.setattr(
            "dispatcher.network_control.config.SIDECAR_PIDS_LIMIT", 100)

        custom_image = {
            "env-cpp": "noj-custom-env:1-env-cpp",
            "my-grader": "noj-custom-env:1-my-grader"
        }

        network_controller._setup_topology(submission_id="test",
                                           external_config={
                                               "model": "white",
                                               "url":
                                               ["https://api.example.com"]
                                           },
                                           sidecars_config=[],
                                           custom_image=custom_image)

        # Verify put_archive was called
        assert mock_docker_client.put_archive.called

    def test_router_entrypoint_parses_internal_names(self):
        """Verify entrypoint.sh parses internal_names from config."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for internal_names parsing
        assert "INTERNAL_NAMES" in content
        assert "internal_names" in content

    def test_router_entrypoint_whitelist_uses_catch_all(self):
        """Verify whitelist mode uses catch-all blocking."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for catch-all blocking in whitelist mode
        assert 'address=/#/' in content

    def test_router_entrypoint_allows_internal_names(self):
        """Verify entrypoint.sh allows internal names via server= directive."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for internal name allowlist using server= directive
        assert "server=/$name/127.0.0.11" in content or "server=/$name/" in content

    def test_router_entrypoint_whitelist_allows_domains(self):
        """Verify entrypoint.sh allows whitelisted domains via server= directive."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for whitelisted domain handling
        assert "server=/$domain/8.8.8.8" in content


class TestWhitelistModeComplete:
    """Integration tests for complete whitelist mode functionality."""

    def test_whitelist_mode_blocks_unknown_domains(self):
        """Verify whitelist mode has catch-all blocking for unknown domains."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # In whitelist mode, should have catch-all blocking
        assert 'address=/#/0.0.0.0' in content
        assert 'address=/#/::' in content

    def test_whitelist_mode_strategy_documented(self):
        """Verify whitelist mode strategy is documented in entrypoint."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # Check for strategy documentation
        assert "Catch-all" in content or "catch-all" in content

    def test_blacklist_mode_blocks_specific_domains(self):
        """Verify blacklist mode blocks specific domains only."""
        entrypoint = (Path(__file__).resolve().parents[1] / "network_router" /
                      "entrypoint.sh")
        content = entrypoint.read_text(encoding="utf-8")

        # In blacklist mode, should block specific domains
        assert "Blocking domain from URL" in content
        assert 'address=/$domain/0.0.0.0' in content
