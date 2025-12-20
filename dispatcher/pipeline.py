import json
import requests as rq

from .utils import (
    logger, )
from .config import (
    BACKEND_API,
    SANDBOX_TOKEN,
    TESTDATA_ROOT,
)


def handle_problem_response(resp: rq.Response):
    if resp.status_code == 404:
        raise ValueError("Problem not found")
    if resp.status_code == 401:
        raise PermissionError()
    if not resp.ok:
        logger().error(f"Error during get problem data [resp: {resp.text}]")
        raise RuntimeError()


# for static analysis
def fetch_problem_rules(problem_id: int) -> dict:
    """
    Fetch static analysis rules.json from backend server
    """

    logger().debug(f"fetch problem rules [problem_id: {problem_id}]")
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/rules",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    try:
        handle_problem_response(resp)
        data = resp.json().get("data", {})
        return data
    except ValueError:
        logger().warning(
            f"Not found problem rules, [problem_id: {problem_id}]")
        return {}
    except Exception as e:
        logger().error(
            f"Error during fetch problem rules, [problem_id: {problem_id}]")
        return {}


def fetch_problem_network_config(problem_id: int) -> dict:
    """
    Fetch network configuration (sidecars & external) from local meta file
    Saved by testdata.py
    """
    meta_path = TESTDATA_ROOT / "meta" / f"{problem_id}.json"
    logger().debug(
        f"(*_*)[In fetch_problem_network_config] Start to find config [problem_id: {problem_id}]"
    )
    try:
        if not meta_path.exists():
            logger().warning(
                f"Meta file not found, [Meta path]: {meta_path} [problem_id]: {problem_id}"
            )
            return {}

        content = meta_path.read_text(encoding="utf-8")
        data = json.loads(content)

        logger().debug(
            f"(*_*)[In fetch_problem_network_config] Read meta content [problem_id: {problem_id}]: {data}"
        )

        network_config = {}

        if "networkAccessRestriction" in data:
            network_config = data["networkAccessRestriction"]
        elif "config" in data and isinstance(data["config"], dict):
            network_config = data["config"].get("networkAccessRestriction", {})

        if network_config is None:
            network_config = {}

        asset_paths = data.get("assetPaths", {})
        if asset_paths.get("network_dockerfile"):
            logger().info(
                f"(*_*) [In fetch_problem_network_config] Detected network_dockerfile in assetPaths, enabling custom_env automatically."
            )

            if "custom_env" not in network_config:
                network_config["custom_env"] = {}
            network_config["custom_env"]["enabled"] = True

        logger().debug(
            f"(*_*)[In fetch_problem_network_config] Fetched network config [problem_id: {problem_id}]: {network_config}"
        )
        return network_config
    except Exception as e:
        logger().error(
            f"(*_*)[In fetch_problem_network_config] Error reading meta: {e} [Meta path]: {meta_path} [problem_id]: {problem_id}"
        )
        return {}
