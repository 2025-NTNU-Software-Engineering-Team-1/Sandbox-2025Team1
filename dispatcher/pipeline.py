import json
import requests as rq

from .utils import (
    logger,
)
from .config import (
    BACKEND_API,
    SANDBOX_TOKEN,
    TESTDATA_ROOT,
)

RULES_DIR = TESTDATA_ROOT / "rules"
RULES_DIR.mkdir(exist_ok=True, parents=True)


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
    rule_path = RULES_DIR / f"{problem_id}.json"
    if rule_path.exists():
        try:
            return json.load(rule_path.open())
        except json.JSONDecodeError:
            pass

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

        with rule_path.open("w") as f:
            json.dump(data, f)

        return data
    except ValueError:
        logger().warning(f"Not found problem rules, [problem_id: {problem_id}]")
        return {}
    except Exception as e:
        logger().error(f"Error during fetch problem rules, [problem_id: {problem_id}]")
        return {}


def fetch_problem_network_config(problem_id: int) -> dict:
    """
    Fetch network configuration (sidecars & ACLs) from backend server
    Similar to fetch_problem_rules
    """
    logger().debug(f"fetch problem network config [problem_id: {problem_id}]")
    resp = rq.get(
        f"{BACKEND_API}/problem/{problem_id}/network",
        params={
            "token": SANDBOX_TOKEN,
        },
    )
    try:
        handle_problem_response(resp)
        return resp.json().get("data", {})
    except ValueError:
        logger().warning(f"Not found network config, [problem_id: {problem_id}]")
        return {}
    except Exception as e:
        logger().error(f"Error fetching network config: {e}")
        return {}
