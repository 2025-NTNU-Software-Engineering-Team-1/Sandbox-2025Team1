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


def _translate_legacy_network_schema(raw_config: dict) -> dict:
    """
    將舊格式 (firewallExtranet/connectWithLocal) 轉換為新格式 (external/sidecars/custom_env)。
    如果已經是新格式則直接返回。
    
    舊格式範例:
    {
        "enabled": true,
        "firewallExtranet": {"mode": "whitelist", "rules": [{"type": "ip", "value": "1.2.3.4"}]},
        "connectWithLocal": {"mode": "whitelist", "rules": [...]}
    }
    
    新格式範例:
    {
        "external": {"model": "White", "ip": [], "url": []},
        "sidecars": [...],
        "custom_env": {"env_list": [...]}
    }
    """
    if not raw_config:
        return {}

    # 檢測是否為新格式（包含 external/sidecars/custom_env 任一欄位）
    new_format_keys = {"external", "sidecars", "custom_env"}
    if new_format_keys & set(raw_config.keys()):
        logger().debug(
            "Network config is already in new format, no translation needed")
        return raw_config

    # 檢測是否為舊格式（包含 firewallExtranet/connectWithLocal）
    legacy_keys = {"firewallExtranet", "connectWithLocal"}
    if not (legacy_keys & set(raw_config.keys())):
        # 既不是新格式也不是舊格式，可能只有 enabled 等欄位
        logger().debug(
            "Network config has no recognizable format, returning as-is")
        return raw_config

    logger().info("Translating legacy network config format to new format")
    result = {}

    # firewallExtranet -> external
    if "firewallExtranet" in raw_config:
        fw = raw_config["firewallExtranet"]
        mode = fw.get("mode", "blacklist")
        rules = fw.get("rules", [])

        # 轉換 model: whitelist -> White, blacklist -> Black
        model = "White" if mode == "whitelist" else "Black"

        # 分離 IP 和 URL 規則
        ip_list = []
        url_list = []
        for rule in rules:
            rule_type = rule.get("type", "")
            value = rule.get("value", "")
            if rule_type == "ip" and value:
                ip_list.append(value)
            elif rule_type == "url" and value:
                url_list.append(value)

        result["external"] = {
            "model": model,
            "ip": ip_list,
            "url": url_list,
        }
        logger().debug(
            f"Translated firewallExtranet to external: {result['external']}")

    # connectWithLocal -> 目前沒有直接對應，記錄警告
    if "connectWithLocal" in raw_config:
        cwl = raw_config["connectWithLocal"]
        logger().warning(
            f"connectWithLocal found in legacy config but no direct mapping exists: {cwl}. "
            "This may need manual configuration as sidecars or custom_env.")
        # 可選：將 connectWithLocal 的本地 IP 規則加入 external 的白名單
        # 這裡先不做自動轉換，因為語意不完全相同

    # 保留 enabled 欄位供後續使用
    if "enabled" in raw_config:
        result["enabled"] = raw_config["enabled"]

    return result


def fetch_problem_network_config(problem_id: int) -> dict:
    """
    Fetch network configuration (sidecars & external) from local meta file
    Saved by testdata.py
    
    支援新舊兩種格式，自動偵測並轉換：
    - 新格式: external/sidecars/custom_env
    - 舊格式: firewallExtranet/connectWithLocal (自動轉換為新格式)
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

        # 自動偵測並轉換舊格式
        network_config = _translate_legacy_network_schema(network_config)

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
