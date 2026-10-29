# -*- coding: utf-8 -*-
"""滴滴官方 MCP Server 的 CLI 封装（Streamable HTTP，手写客户端，零依赖）。

官方不提供 Skill，只提供 MCP 端点；这里把它翻译成普通命令行：
    didimcp.py tools                     # 列出工具
    didimcp.py call taxi_estimate --json '{"...":"..."}'

Key 放 ~/.didi/key.txt（可用 DIDI_DATA_DIR 覆盖）
默认走沙箱（Mock，不产生真实订单），加 --prod 才连生产。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DATA_DIR = Path(os.environ.get("DIDI_DATA_DIR") or Path.home() / ".didi")
KEY_FILE = DATA_DIR / "key.txt"
PROD = "https://mcp.didichuxing.com/mcp-servers"
SANDBOX = "https://mcp.didichuxing.com/mcp-servers-sandbox"
PROTOCOL = "2025-06-18"


def load_key():
    if not KEY_FILE.exists():
        raise SystemExit("缺少 %s（去 mcp.didichuxing.com 控制台激活个人 MCP Key）" % KEY_FILE)
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key or key.startswith("<"):
        raise SystemExit("key.txt 里还是占位符，先填真实 Key")
    return key


class Session:
    def __init__(self, base, key):
        self.url = "%s?key=%s" % (base, key)
        self.session_id = None
        self._id = 0

    def _post(self, payload, timeout=60):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.session_id:
            req.add_header("Mcp-Session-Id", self.session_id)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:600]
            raise SystemExit("HTTP %s: %s" % (exc.code, detail))
        if "text/event-stream" in ctype:
            return self._parse_sse(raw)
        return json.loads(raw) if raw.strip() else {}

    @staticmethod
    def _parse_sse(raw):
        out = None
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        out = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
        return out or {}

    def call(self, method, params=None):
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        resp = self._post(payload)
        if "error" in resp:
            raise SystemExit("MCP error: %s" % json.dumps(resp["error"], ensure_ascii=False))
        return resp.get("result", resp)

    def initialize(self):
        result = self.call("initialize", {
            "protocolVersion": PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "axon-cli", "version": "1.0"},
        })
        # 按规范补一条 initialized 通知（无 id，失败不影响后续）
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except SystemExit:
            pass
        return result


def main():
    ap = argparse.ArgumentParser(description="滴滴 MCP CLI（默认沙箱）")
    ap.add_argument("--prod", action="store_true", help="连生产环境，会产生真实订单与费用")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools", help="列出可用工具")
    p = sub.add_parser("call", help="调用工具")
    p.add_argument("tool")
    p.add_argument("--json", default="{}", help="工具入参 JSON")
    args = ap.parse_args()

    sess = Session(PROD if args.prod else SANDBOX, load_key())
    info = sess.initialize()
    server = (info.get("serverInfo") or {}).get("name", "?")
    env = "生产" if args.prod else "沙箱"

    if args.cmd == "tools":
        tools = sess.call("tools/list", {}).get("tools", [])
        print("环境=%s server=%s 工具数=%d" % (env, server, len(tools)))
        for t in tools:
            print("- %-28s %s" % (t.get("name"), (t.get("description") or "")[:70]))
        return 0

    payload = json.loads(args.json)
    result = sess.call("tools/call", {"name": args.tool, "arguments": payload})
    print("环境=%s 工具=%s" % (env, args.tool))
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if item.get("type") == "text":
                print(item.get("text", ""))
            else:
                print(json.dumps(item, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
