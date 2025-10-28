import json
import requests as rq

from .utils import (
    logger,
)
from .config import (
    BACKEND_API,
    SANDBOX_TOKEN,
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
        content = json.dumps(resp.json()["data"])
        return content
        # suppose in "rules"
    except ValueError:
        logger().warning(f"Not found problem rules, [problem_id: {problem_id}]")
        return None
    except Exception as e:
        logger().error(f"Error during fetch problem rules, [problem_id: {problem_id}]")
        return None
