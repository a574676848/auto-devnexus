# -*- coding: utf-8 -*-
"""百度网盘 CLI（OAuth 2.0 授权码模式 + REST API）。

状态：骨架已就绪，等待 AppKey/SecretKey 后实测。凭据放
~/.baidupan/credentials.json

用法：
    python bdpan.py auth             # 打印授权链接
    python bdpan.py token <code>     # 用授权码换 token 并落盘
    python bdpan.py refresh          # 手动刷新 token
    python bdpan.py whoami           # 账号信息
    python bdpan.py quota            # 容量
    python bdpan.py ls /目录         # 列目录
    python bdpan.py search 关键词    # 搜索
    python bdpan.py link /路径       # 取下载直链
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(os.environ.get("BAIDUPAN_DATA_DIR") or Path.home() / ".baidupan")
CRED = BASE / "credentials.json"
PAN_UA = "pan.baidu.com"


def load():
    if not CRED.exists():
        raise SystemExit("缺少 %s（先按 credentials.example.json 填 AppKey/SecretKey）" % CRED)
    return json.loads(CRED.read_text(encoding="utf-8"))


def save(cred):
    CRED.write_text(json.dumps(cred, ensure_ascii=False, indent=2), encoding="utf-8")


def http(url, data=None, headers=None, timeout=30):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method="POST" if body else "GET")
    req.add_header("User-Agent", PAN_UA)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_token(cred):
    if cred.get("access_token") and cred.get("expires_at", 0) > time.time() + 300:
        return cred["access_token"]
    if not cred.get("refresh_token"):
        raise SystemExit("没有可用 token，先执行 auth 授权")
    url = "https://openapi.baidu.com/oauth/2.0/token?" + urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": cred["refresh_token"],
        "client_id": cred["api_key"],
        "client_secret": cred["secret_key"],
    })
    tok = http(url)
    if "access_token" not in tok:
        raise SystemExit("刷新失败：%s" % tok)
    cred.update({
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token", cred["refresh_token"]),
        "expires_at": int(time.time()) + int(tok.get("expires_in", 2592000)),
    })
    save(cred)
    return cred["access_token"]


def api(path, params, token):
    params = dict(params)
    params["access_token"] = token
    return http(path + "?" + urllib.parse.urlencode(params))


def main():
    ap = argparse.ArgumentParser(description="百度网盘 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth")
    p = sub.add_parser("token"); p.add_argument("code")
    sub.add_parser("refresh"); sub.add_parser("whoami"); sub.add_parser("quota")
    p = sub.add_parser("ls"); p.add_argument("dir", nargs="?", default="/")
    p = sub.add_parser("search"); p.add_argument("key")
    p = sub.add_parser("link"); p.add_argument("path")
    args = ap.parse_args()

    cred = load()

    if args.cmd == "auth":
        url = "https://openapi.baidu.com/oauth/2.0/authorize?" + urllib.parse.urlencode({
            "response_type": "code",
            "client_id": cred["api_key"],
            "redirect_uri": cred.get("redirect_uri", "oob"),
            "scope": "basic,netdisk",
            "display": "mobile",
        })
        print(url)
        return 0

    if args.cmd == "token":
        tok = http("https://openapi.baidu.com/oauth/2.0/token?" + urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": args.code,
            "client_id": cred["api_key"],
            "client_secret": cred["secret_key"],
            "redirect_uri": cred.get("redirect_uri", "oob"),
        }))
        if "access_token" not in tok:
            print(json.dumps(tok, ensure_ascii=False))
            return 1
        cred.update({
            "access_token": tok["access_token"],
            "refresh_token": tok.get("refresh_token", ""),
            "expires_at": int(time.time()) + int(tok.get("expires_in", 2592000)),
        })
        save(cred)
        print("token saved, expires_in=%s" % tok.get("expires_in"))
        return 0

    token = ensure_token(cred)

    if args.cmd == "refresh":
        print("refreshed, expires_at=%s" % cred["expires_at"])
    elif args.cmd == "whoami":
        print(json.dumps(api("https://pan.baidu.com/rest/2.0/xpan/nas", {"method": "uinfo"}, token), ensure_ascii=False, indent=2))
    elif args.cmd == "quota":
        print(json.dumps(api("https://pan.baidu.com/api/quota", {}, token), ensure_ascii=False, indent=2))
    elif args.cmd == "ls":
        res = api("https://pan.baidu.com/rest/2.0/xpan/file", {"method": "list", "dir": args.dir, "limit": 100}, token)
        for item in res.get("list", []):
            kind = "DIR " if item.get("isdir") else "FILE"
            print("%s %-50s %s" % (kind, item.get("server_filename"), item.get("size", "")))
        if not res.get("list"):
            print(json.dumps(res, ensure_ascii=False))
    elif args.cmd == "search":
        res = api("https://pan.baidu.com/rest/2.0/xpan/file", {"method": "search", "key": args.key, "recursion": 1}, token)
        for item in res.get("list", [])[:50]:
            print("%-60s %s" % (item.get("path"), item.get("size", "")))
        if not res.get("list"):
            print(json.dumps(res, ensure_ascii=False))
    elif args.cmd == "link":
        fsids = api("https://pan.baidu.com/rest/2.0/xpan/file", {"method": "search", "key": args.path.rsplit("/", 1)[-1]}, token)
        print(json.dumps(fsids, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
