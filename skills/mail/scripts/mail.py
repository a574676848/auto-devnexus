# -*- coding: utf-8 -*-
"""多账号邮件 CLI（IMAP 读 + SMTP 发，标准库实现）。

账号配置：~/.mail/accounts.json（可用 MAIL_DATA_DIR 覆盖）
示例见同目录 accounts.example.json。

用法：
    python mail.py accounts
    python mail.py inbox --account qq --limit 10
    python mail.py inbox --account qq --unread
    python mail.py read --account qq --uid 1234
    python mail.py search --account qq --key 发票
    python mail.py send --account qq --to a@b.com --subject 标题 --body 正文
"""
import argparse
import email
import email.header
import imaplib
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, parsedate_to_datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("MAIL_DATA_DIR") or Path.home() / ".mail")
CONF = DATA_DIR / "accounts.json"


def load_conf():
    if not CONF.exists():
        raise SystemExit("缺少 %s（按 accounts.example.json 填写）" % CONF)
    return json.loads(CONF.read_text(encoding="utf-8"))


def pick(conf, name):
    if name not in conf:
        raise SystemExit("未配置账号 %s，可选：%s" % (name, ", ".join(conf)))
    return conf[name]


def _safe_decode(raw, charset):
    # 邮件头声明的 charset 五花八门，"unknown-8bit" 这种不是合法编码名，直接 decode 会抛 LookupError
    for enc in (charset, "utf-8", "gb18030", "latin-1"):
        if not enc:
            continue
        try:
            return raw.decode(enc, "replace")
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def decode(value):
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(_safe_decode(text, charset))
        else:
            out.append(text)
    return "".join(out)


def imap_conn(cfg):
    conn = imaplib.IMAP4_SSL(cfg["imap_host"], cfg.get("imap_port", 993))
    conn.login(cfg["address"], cfg["password"])
    # 网易系（163/126/yeah.net）登录后必须先报客户端 ID，否则后续 SELECT 会返回
    # "Unsafe Login. Please contact kefu@188.com"。其它服务商不发这条也无害，这里只为网易触发。
    if any(mark in cfg["imap_host"] for mark in ("163.com", "126.com", "yeah.net")):
        try:
            conn.xatom("ID", '("name" "axon-mail" "version" "1.0" "vendor" "axon")')
        except Exception:
            pass
    return conn


def cmd_accounts(args):
    conf = load_conf()
    for name, cfg in conf.items():
        print("%-8s %s" % (name, cfg["address"]))


def cmd_inbox(args):
    cfg = pick(load_conf(), args.account)
    conn = imap_conn(cfg)
    try:
        conn.select("INBOX", readonly=True)
        status, data = conn.uid("search", None, "UNSEEN" if args.unread else "ALL")
        uids = data[0].split()
        uids = uids[-args.limit:]
        if not uids:
            print("没有匹配的邮件")
            return 0
        for uid in reversed(uids):
            status, parts = conn.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            raw = parts[0][1]
            msg = email.message_from_bytes(raw)
            print("uid=%-8s %-8s %s | %s" % (
                uid.decode(),
                "",
                parsedate_to_datetime(msg.get("Date", "")).strftime("%m-%d %H:%M") if msg.get("Date") else "?",
                decode(msg.get("From", ""))[:40],
            ))
            print("           %s" % decode(msg.get("Subject", ""))[:90])
    finally:
        conn.logout()
    return 0


def cmd_read(args):
    cfg = pick(load_conf(), args.account)
    conn = imap_conn(cfg)
    try:
        conn.select("INBOX", readonly=True)
        status, parts = conn.uid("fetch", args.uid, "(RFC822)")
        msg = email.message_from_bytes(parts[0][1])
        print("From:    %s" % decode(msg.get("From", "")))
        print("To:      %s" % decode(msg.get("To", "")))
        print("Date:    %s" % msg.get("Date", ""))
        print("Subject: %s" % decode(msg.get("Subject", "")))
        print("-" * 60)
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True) or b""
                    print(payload.decode(part.get_content_charset() or "utf-8", "replace")[:4000])
                    break
        else:
            payload = msg.get_payload(decode=True) or b""
            print(payload.decode(msg.get_content_charset() or "utf-8", "replace")[:4000])
    finally:
        conn.logout()
    return 0


def cmd_search(args):
    cfg = pick(load_conf(), args.account)
    conn = imap_conn(cfg)
    try:
        conn.select("INBOX", readonly=True)
        status, data = conn.uid("search", None, "TEXT", '"%s"' % args.key)
        uids = data[0].split()[-args.limit:]
        for uid in reversed(uids):
            status, parts = conn.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            msg = email.message_from_bytes(parts[0][1])
            print("uid=%-8s %s | %s" % (uid.decode(), decode(msg.get("From", ""))[:36], decode(msg.get("Subject", ""))[:70]))
        if not uids:
            print("没有命中")
    finally:
        conn.logout()
    return 0


def cmd_send(args):
    cfg = pick(load_conf(), args.account)
    msg = MIMEText(args.body, "plain", "utf-8")
    msg["From"] = formataddr(("", cfg["address"]))
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg["Date"] = formatdate(localtime=True)
    with smtplib.SMTP_SSL(cfg["smtp_host"], cfg.get("smtp_port", 465), timeout=30) as smtp:
        smtp.login(cfg["address"], cfg["password"])
        smtp.sendmail(cfg["address"], [args.to], msg.as_string())
    print("sent to %s" % args.to)
    return 0


def main():
    ap = argparse.ArgumentParser(description="多账号邮件 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("accounts").set_defaults(func=cmd_accounts)

    p = sub.add_parser("inbox")
    p.add_argument("--account", required=True)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--unread", action="store_true")
    p.set_defaults(func=cmd_inbox)

    p = sub.add_parser("read")
    p.add_argument("--account", required=True)
    p.add_argument("--uid", required=True)
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("search")
    p.add_argument("--account", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("send")
    p.add_argument("--account", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.set_defaults(func=cmd_send)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
