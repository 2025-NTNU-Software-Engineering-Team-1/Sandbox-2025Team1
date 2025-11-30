import pytest
from unittest.mock import MagicMock, patch, call
from dispatcher.network_control import NetworkController
from dispatcher.meta import Sidecar


@pytest.fixture
def mock_docker_client():
    with patch("dispatcher.network_control.docker.APIClient") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def network_controller(mock_docker_client):
    nc = NetworkController(docker_url="unix://fake.sock")
    return nc


def test_ensure_sidecar_images_pulls_missing_image(network_controller,
                                                   mock_docker_client):
    # Arrange
    import docker

    sidecars = [Sidecar(name="db", image="mysql:5.7", env={}, args=[])]

    # mock inspect_image push ImageNotFound
    mock_docker_client.inspect_image.side_effect = docker.errors.ImageNotFound(
        "Missing")

    # Act
    network_controller.ensure_sidecar_images(sidecars)

    # Assert
    mock_docker_client.inspect_image.assert_called_with("mysql:5.7")
    mock_docker_client.pull.assert_called_with("mysql:5.7")


def test_ensure_sidecar_images_skips_existing_image(network_controller,
                                                    mock_docker_client):
    # Arrange
    sidecars = [Sidecar(name="db", image="mysql:5.7", env={}, args=[])]
    # mock inspect_image
    mock_docker_client.inspect_image.return_value = {"Id": "sha256:..."}

    # Act
    network_controller.ensure_sidecar_images(sidecars)

    # Assert
    mock_docker_client.inspect_image.assert_called_with("mysql:5.7")
    mock_docker_client.pull.assert_not_called()


def test_setup_sidecars_creates_network_and_containers(network_controller,
                                                       mock_docker_client):
    # Arrange
    submission_id = "test-sub"
    sidecars = [
        Sidecar(name="db",
                image="mysql:5.7",
                env={"KEY": "VAL"},
                args=["--arg"])
    ]
    mock_docker_client.create_network.return_value = {"Id": "net-123"}
    mock_docker_client.create_container.return_value = {"Id": "container-456"}

    # Act
    container_ids = network_controller.setup_sidecars(submission_id, sidecars)

    # Assert
    # 1. Check Network Creation
    mock_docker_client.create_network.assert_called_with(
        name=f"noj-net-{submission_id}",
        driver="bridge",
        internal=True,
        check_duplicate=True,
    )
    # 2. Check Container Creation
    mock_docker_client.create_container.assert_called()
    call_args = mock_docker_client.create_container.call_args[1]
    assert call_args["image"] == "mysql:5.7"
    assert "KEY=VAL" in call_args["environment"]
    assert call_args["command"] == ["--arg"]

    # 3. Check Container Start
    mock_docker_client.start.assert_called()
    assert container_ids == ["container-456"]


def test_cleanup_removes_resources(network_controller, mock_docker_client):
    # Arrange
    submission_id = "test-sub"
    # replicate existing resources
    network_controller.sidecar_resources[submission_id] = {
        "network_name": "net-test",
        "container_ids": ["c1", "c2"],
        "router_id": "r1",
    }

    # Act
    network_controller.cleanup(submission_id)

    # Assert
    # Verify that remove_container and remove_network were called
    assert mock_docker_client.remove_container.call_count >= 3  # r1, c1, c2
    mock_docker_client.remove_container.assert_any_call("r1",
                                                        v=True,
                                                        force=True)
    mock_docker_client.remove_container.assert_any_call("c1",
                                                        v=True,
                                                        force=True)
    mock_docker_client.remove_network.assert_called_with("net-test")
    # Confirm resource map is cleared
    assert submission_id not in network_controller.sidecar_resources
