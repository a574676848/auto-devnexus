# -*- coding: utf-8 -*-
"""Cloudflare API CLI（零依赖，标准库 urllib）。

凭据：~/.cloudflare/config.json（可用 CLOUDFLARE_CONFIG 指定其它位置）
    {"token": "...", "account_id": "...", "default_zone": "example.com"}
token 也可用环境变量 CLOUDFLARE_API_TOKEN 覆盖。

用法：
    cf.py zones                                   # 列域名
    cf.py dns [zone]                              # 列 DNS 记录
    cf.py dns-add <zone> --type A --name x --content 1.2.3.4 [--proxied] [--ttl 1]
    cf.py dns-update <zone> --id <rec> [--content 1.2.3.4] [--proxied/--no-proxied] [--ttl 1]
    cf.py dns-del <zone> --id <rec> --yes
    cf.py purge <zone> --all                      # 清全站缓存
    cf.py purge <zone> --urls https://a.com/1
    cf.py raw GET /user/tokens/verify             # 逃生口
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.cloudflare.com/client/v4"
CONF = Path(os.environ.get("CLOUDFLARE_CONFIG")
            or Path.home() / ".cloudflare" / "config.json")


def load_conf():
    conf = {}
    if CONF.is_file():
        conf = json.loads(CONF.read_text(encoding="utf-8-sig"))
    token = (os.environ.get("CLOUDFLARE_API_TOKEN") or conf.get("token") or "").strip()
    if not token:
        raise SystemExit(
            "缺少 token。写入 %s 的 token 字段，或设置环境变量 CLOUDFLARE_API_TOKEN" % CONF
        )
    conf["token"] = token
    return conf


class CF:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, body=None):
        url = API + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(detail)
                errs = payload.get("errors") or []
                if errs:
                    detail = "; ".join(
                        "%s %s" % (e.get("code"), e.get("message")) for e in errs[:3]
                    )
            except json.JSONDecodeError:
                detail = detail[:500]
            raise SystemExit("HTTP %s: %s" % (exc.code, detail))
        if not raw.strip():
            return {}
        payload = json.loads(raw)
        if not payload.get("success", True):
            errs = payload.get("errors") or []
            msg = "; ".join("%s %s" % (e.get("code"), e.get("message")) for e in errs[:3])
            raise SystemExit("API 报错: " + (msg or raw[:300]))
        return payload.get("result")


def resolve_zone(cf, conf, name):
    name = name or conf.get("default_zone")
    if not name:
        raise SystemExit("没指定 zone，配置里也没 default_zone")
    if len(name) == 32 and all(c in "0123456789abcdef" for c in name.lower()):
        return name, name
    zones = cf.call("GET", "/zones?per_page=50")
    for z in zones or []:
        if z["name"] == name:
            return z["id"], z["name"]
    names = ", ".join(z["name"] for z in zones or []) or "(空)"
    raise SystemExit("找不到域名 %s，可选：%s" % (name, names))


def cmd_zones(cf, args):
    for z in cf.call("GET", "/zones?per_page=50") or []:
        print("%-28s %-8s %s" % (z["name"], z["status"], z["id"]))
    return 0


def cmd_dns(cf, args, conf):
    zid, zname = resolve_zone(cf, conf, args.zone)
    recs = cf.call("GET", "/zones/%s/dns_records?per_page=100" % zid) or []
    print("== %s  %d 条 ==" % (zname, len(recs)))
    for r in sorted(recs, key=lambda x: (x["type"], x["name"])):
        print("%-6s %-40s %-32s proxy=%-5s ttl=%-5s %s" % (
            r["type"], r["name"], r["content"][:32], r["proxied"], r.get("ttl"), r["id"]))
    return 0


def cmd_dns_add(cf, args, conf):
    zid, zname = resolve_zone(cf, conf, args.zone)
    body = {
        "type": args.type,
        "name": args.name,
        "content": args.content,
        "ttl": args.ttl,
    }
    if args.proxied:
        body["proxied"] = True
    res = cf.call("POST", "/zones/%s/dns_records" % zid, body)
    print("已创建  %s %s -> %s  id=%s" % (res["type"], res["name"], res["content"], res["id"]))
    return 0


def cmd_dns_update(cf, args, conf):
    zid, zname = resolve_zone(cf, conf, args.zone)
    body = {}
    if args.content:
        body["content"] = args.content
    if args.ttl is not None:
        body["ttl"] = args.ttl
    if args.proxied is not None:
        body["proxied"] = args.proxied
    if not body:
        raise SystemExit("没有要改的字段")
    res = cf.call("PATCH", "/zones/%s/dns_records/%s" % (zid, args.id), body)
    print("已更新  %s %s -> %s proxy=%s" % (res["type"], res["name"], res["content"], res["proxied"]))
    return 0


def cmd_dns_del(cf, args, conf):
    if not args.yes:
        raise SystemExit("删除 DNS 记录不可逆，确认要删请加 --yes")
    zid, zname = resolve_zone(cf, conf, args.zone)
    res = cf.call("DELETE", "/zones/%s/dns_records/%s" % (zid, args.id))
    print("已删除  id=%s  %s" % (args.id, res.get("id") if isinstance(res, dict) else res))
    return 0


def cmd_purge(cf, args, conf):
    zid, zname = resolve_zone(cf, conf, args.zone)
    if args.all:
        body = {"purge_everything": True}
    elif args.urls:
        body = {"files": args.urls}
    else:
        raise SystemExit("要么 --all，要么 --urls")
    cf.call("POST", "/zones/%s/purge_cache" % zid, body)
    print("已清理缓存：%s  %s" % (zname, "全站" if args.all else "%d 个 URL" % len(args.urls)))
    return 0


def cmd_raw(cf, args, conf):
    body = json.loads(args.data) if args.data else None
    res = cf.call(args.method.upper(), args.path, body)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Cloudflare API CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("zones", help="列出账号下所有域名")

    p = sub.add_parser("dns", help="列出 DNS 记录")
    p.add_argument("zone", nargs="?")

    p = sub.add_parser("dns-add", help="新增 DNS 记录")
    p.add_argument("zone", nargs="?")
    p.add_argument("--type", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--content", required=True)
    p.add_argument("--ttl", type=int, default=1, help="1=自动")
    p.add_argument("--proxied", action="store_true", help="走 Cloudflare 橙云代理")

    p = sub.add_parser("dns-update", help="修改 DNS 记录")
    p.add_argument("zone", nargs="?")
    p.add_argument("--id", required=True)
    p.add_argument("--content")
    p.add_argument("--ttl", type=int)
    p.add_argument("--proxied", action="store_true", default=None)
    p.add_argument("--no-proxied", dest="proxied", action="store_false")

    p = sub.add_parser("dns-del", help="删除 DNS 记录")
    p.add_argument("zone", nargs="?")
    p.add_argument("--id", required=True)
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("purge", help="清理缓存")
    p.add_argument("zone", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--urls", nargs="*")

    p = sub.add_parser("raw", help="原始 API 调用")
    p.add_argument("method")
    p.add_argument("path")
    p.add_argument("--data")

    args = ap.parse_args()
    conf = load_conf()
    cf = CF(conf["token"])
    handler = {
        "zones": lambda: cmd_zones(cf, args),
        "dns": lambda: cmd_dns(cf, args, conf),
        "dns-add": lambda: cmd_dns_add(cf, args, conf),
        "dns-update": lambda: cmd_dns_update(cf, args, conf),
        "dns-del": lambda: cmd_dns_del(cf, args, conf),
        "purge": lambda: cmd_purge(cf, args, conf),
        "raw": lambda: cmd_raw(cf, args, conf),
    }[args.cmd]()
    return handler or 0


if __name__ == "__main__":
    sys.exit(main())
