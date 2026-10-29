# -*- coding: utf-8 -*-
"""瑞幸咖啡官方 MCP Server 的 CLI 封装（Streamable HTTP，手写客户端，零依赖）。

官方 my-coffee Skill 是 instructionOnly，本身不含可执行代码，只声明依赖 MCP Server。
这里把它翻译成普通命令行：

    luckin.py tools                  # 列出全部工具
    luckin.py schema previewOrder    # 看单个工具的入参 schema
    luckin.py call queryShopList --json '{"longitude":118.1,"latitude":24.5}'

Token 读取优先级：环境变量 LUCKIN_MCP_TOKEN > <data>/ruijin/token.txt > ~/.my-coffee/LUCKIN_MCP_TOKEN
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://gwmcp.lkcoffee.com/order/user/mcp"
PROTOCOL = "2025-06-18"
DATA_DIR = Path(os.environ.get("LUCKIN_DATA_DIR") or Path.home() / ".my-coffee")
TOKEN_FILE = DATA_DIR / "token.txt"
TOKEN_FILE_FALLBACK = DATA_DIR / "LUCKIN_MCP_TOKEN"


def load_token():
    tok = (os.environ.get("LUCKIN_MCP_TOKEN") or "").strip()
    if tok:
        return tok, "env"
    for path, tag in ((TOKEN_FILE, "file"), (TOKEN_FILE_FALLBACK, "file~")):
        try:
            if path.is_file():
                tok = path.read_text(encoding="utf-8-sig").strip()
                if tok and not tok.startswith("<"):
                    return tok, str(path)
        except OSError:
            continue
    raise SystemExit(
        "缺少瑞幸 token。去 https://open.lkcoffee.com/mcp 登录创建，"
        "写入 %s 或设置环境变量 LUCKIN_MCP_TOKEN" % TOKEN_FILE
    )


class Session:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.session_id = None
        self._id = 0

    def _post(self, payload, timeout=60):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        # 缺了 text/event-stream 网关会直接 400
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("Authorization", "Bearer " + self.token)
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
            hint = ""
            if exc.code in (401, 403):
                hint = "（token 失效或不完整？去 https://open.lkcoffee.com/mcp 重新创建）"
            raise SystemExit("HTTP %s%s: %s" % (exc.code, hint, detail))
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
            "clientInfo": {"name": "axon-luckin-cli", "version": "1.0"},
        })
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except SystemExit:
            pass
        return result


def render(result):
    """优先打印结构化内容；否则打印文本块。"""
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
    ap = argparse.ArgumentParser(description="瑞幸咖啡 MCP CLI")
    ap.add_argument("--url", default=os.environ.get("LUCKIN_MCP_URL", DEFAULT_URL))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools", help="列出全部工具")
    p = sub.add_parser("schema", help="查看工具入参 schema")
    p.add_argument("tool")
    p = sub.add_parser("call", help="调用工具")
    p.add_argument("tool")
    p.add_argument("--json", default="{}", help="工具入参 JSON")
    args = ap.parse_args()

    token, src = load_token()
    sess = Session(args.url, token)
    info = sess.initialize()
    server = (info.get("serverInfo") or {}).get("name", "?")

    if args.cmd == "tools":
        tools = sess.call("tools/list", {}).get("tools", [])
        print("server=%s 工具数=%d token 来源=%s" % (server, len(tools), src))
        for t in tools:
            print("- %-28s %s" % (t.get("name"), (t.get("description") or "").replace("\n", " ")[:80]))
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
