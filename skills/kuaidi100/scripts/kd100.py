# -*- coding: utf-8 -*-
"""快递100 官方 MCP Server 的 CLI 封装（Streamable HTTP，零依赖手写客户端）。

官方端点（key 走 query 参数，不是 header）：
    https://api.kuaidi100.com/mcp/streamable?key=<KUAIDI100_API_KEY>

用法：
    kd100.py tools                                  # 列出工具
    kd100.py schema query_trace                     # 看入参 schema
    kd100.py call query_trace --json '{"num":"...","com":"yuantong"}'

key 读取优先级：环境变量 KUAIDI100_API_KEY > <data>/kuaidi100/key.txt
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.kuaidi100.com/mcp/streamable"
PROTOCOL = "2025-06-18"
DATA_DIR = Path(os.environ.get("KUAIDI100_DATA_DIR") or Path.home() / ".kuaidi100")
KEY_FILE = DATA_DIR / "key.txt"


def load_key():
    key = (os.environ.get("KUAIDI100_API_KEY") or "").strip()
    if key:
        return key, "env"
    try:
        if KEY_FILE.is_file():
            key = KEY_FILE.read_text(encoding="utf-8-sig").strip()
            if key and not key.startswith("<"):
                return key, str(KEY_FILE)
    except OSError:
        pass
    raise SystemExit(
        "缺少快递100 API KEY。去 https://api.kuaidi100.com/ 注册后在管理后台取 KEY，"
        "写入 %s 或设置环境变量 KUAIDI100_API_KEY" % KEY_FILE
    )


class Session:
    def __init__(self, url, key):
        self.url = url + "?key=" + urllib.parse.quote(key)
        self.session_id = None
        self._id = 0

    def _post(self, payload, timeout=60):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise SystemExit("HTTP %s: %s" % (exc.code, detail))
        except urllib.error.URLError as exc:
            raise SystemExit("网络不可达: %s" % exc.reason)
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
        if isinstance(resp, dict) and "error" in resp:
            raise SystemExit("MCP error: %s" % json.dumps(resp["error"], ensure_ascii=False))
        return resp.get("result", resp) if isinstance(resp, dict) else resp

    def initialize(self):
        result = self.call("initialize", {
            "protocolVersion": PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "axon-kd100-cli", "version": "1.0"},
        })
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except SystemExit:
            pass
        return result


def render(result):
    if not isinstance(result, dict):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if result.get("structuredContent") is not None:
        print(json.dumps(result["structuredContent"], ensure_ascii=False, indent=2))
        return
    content = result.get("content")
    if isinstance(content, list) and content:
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                try:
                    print(json.dumps(json.loads(text), ensure_ascii=False, indent=2))
                except (json.JSONDecodeError, TypeError):
                    print(text)
            else:
                print(json.dumps(item, ensure_ascii=False))
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="快递100 MCP CLI")
    ap.add_argument("--url", default=os.environ.get("KUAIDI100_MCP_URL", BASE))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools", help="列出全部工具")
    p = sub.add_parser("schema", help="查看工具入参 schema")
    p.add_argument("tool")
    p = sub.add_parser("call", help="调用工具")
    p.add_argument("tool")
    p.add_argument("--json", default="{}", help="工具入参 JSON")
    args = ap.parse_args()

    key, src = load_key()
    sess = Session(args.url, key)
    info = sess.initialize()
    server = (info.get("serverInfo") or {}).get("name", "?")

    if args.cmd == "tools":
        tools = sess.call("tools/list", {}).get("tools", [])
        print("server=%s 工具数=%d key 来源=%s" % (server, len(tools), src))
        for t in tools:
            print("- %-32s %s" % (t.get("name"), (t.get("description") or "").replace("\n", " ")[:80]))
        return 0

    if args.cmd == "schema":
        for t in sess.call("tools/list", {}).get("tools", []):
            if t.get("name") == args.tool:
                print(json.dumps(t, ensure_ascii=False, indent=2))
                return 0
        raise SystemExit("没有名为 %s 的工具" % args.tool)

    try:
        payload = json.loads(args.json)
    except json.JSONDecodeError as exc:
        raise SystemExit("--json 不是合法 JSON: %s" % exc)
    if not isinstance(payload, dict):
        raise SystemExit("--json 必须是 JSON 对象")
    result = sess.call("tools/call", {"name": args.tool, "arguments": payload})
    if isinstance(result, dict) and result.get("isError"):
        sys.stderr.write("工具返回错误\n")
    render(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
