# -*- coding: utf-8 -*-
"""米家控制脚本：走 Home Assistant REST API。

凭据与地址来自 ~/.mijia/（可用 MIJIA_DATA_DIR 覆盖）。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(os.environ.get("MIJIA_DATA_DIR") or Path.home() / ".mijia")


def load_conf():
    cfg_path = BASE / "ha.json"
    if not cfg_path.exists():
        raise SystemExit("缺少 %s，米家尚未接通" % cfg_path)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    token_path = BASE / "ha_mcp_token.txt"
    token = token_path.read_text(encoding="ascii").strip() if token_path.exists() else cfg["access_token"]
    return cfg["url"].rstrip("/"), token


def api(url, token, path, method="GET", payload=None, timeout=30):
    req = urllib.request.Request(url + path, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=body, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit("HTTP %s: %s" % (exc.code, detail))
    return json.loads(raw) if raw else None


def states(url, token):
    return api(url, token, "/api/states")


def cmd_entities(args):
    url, token = load_conf()
    rows = states(url, token)
    out = []
    for item in rows:
        eid = item["entity_id"]
        if args.domain and not eid.startswith(args.domain + "."):
            continue
        name = item.get("attributes", {}).get("friendly_name", "")
        if args.grep and args.grep not in eid and args.grep not in name:
            continue
        out.append((eid, item["state"], name))
    for eid, state, name in sorted(out):
        print("%-58s %-12s %s" % (eid, state, name))
    print("--- %d 个实体 ---" % len(out))


def cmd_state(args):
    url, token = load_conf()
    item = api(url, token, "/api/states/" + args.entity)
    attrs = {k: v for k, v in item.get("attributes", {}).items()}
    print("entity=%s state=%s name=%s" % (item["entity_id"], item["state"], attrs.get("friendly_name", "")))
    keep = {k: attrs[k] for k in ("brightness", "color_temp_kelvin", "rgb_color", "current_position", "device_class", "unit_of_measurement", "last_changed") if k in attrs}
    if keep:
        print(json.dumps(keep, ensure_ascii=False))


def call_service(args):
    domain, _, service = args.target.partition(".")
    if not service:
        raise SystemExit("服务名格式应为 domain.service，例如 light.turn_on")
    payload = {}
    if args.entity:
        payload["entity_id"] = args.entity
    if args.data:
        payload.update(json.loads(args.data))
    url, token = load_conf()
    api(url, token, "/api/services/%s/%s" % (domain, service), method="POST", payload=payload)
    print("ok %s %s %s" % (domain, service, json.dumps(payload, ensure_ascii=False)))


def cmd_simple(service):
    def run(args):
        args.target = "homeassistant." + service
        call_service(args)
    return run


def cmd_scenes(args):
    url, token = load_conf()
    rows = states(url, token)
    found = [(r["entity_id"], r["state"], r["attributes"].get("friendly_name", "")) for r in rows if r["entity_id"].startswith("scene.")]
    for eid, state, name in sorted(found):
        print("%-50s %-10s %s" % (eid, state, name))
    print("--- %d 个场景 ---" % len(found))


def main():
    ap = argparse.ArgumentParser(description="米家 / Home Assistant 控制")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("entities", help="列出实体")
    p.add_argument("--domain")
    p.add_argument("--grep")
    p.set_defaults(func=cmd_entities)

    p = sub.add_parser("state", help="查看单个实体")
    p.add_argument("entity")
    p.set_defaults(func=cmd_state)

    p = sub.add_parser("service", help="调用任意 HA 服务")
    p.add_argument("target", help="domain.service")
    p.add_argument("--entity")
    p.add_argument("--data")
    p.set_defaults(func=call_service)

    for name in ("on", "off", "toggle"):
        p = sub.add_parser(name, help="%s 一个实体" % name)
        p.add_argument("entity")
        p.set_defaults(func=cmd_simple("turn_" + name), entity=None, data=None, target="homeassistant." + name)

    p = sub.add_parser("scenes", help="列出场景")
    p.set_defaults(func=cmd_scenes)

    args = ap.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
