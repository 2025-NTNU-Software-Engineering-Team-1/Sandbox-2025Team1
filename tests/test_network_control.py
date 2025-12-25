from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch, call
from dispatcher.network_control import NetworkController
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
    network_controller._setup_topology(submission_id=submission_id,
                                       external_config={},
                                       sidecars_config=sidecars_config,
                                       custom_image=None)

    # Assert
    # 1. Check Network Creation (internal=True for sidecar-only)
    mock_docker_client.create_network.assert_called_with(
        f"noj-net-{submission_id}",
        driver="bridge",
        internal=True,
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
