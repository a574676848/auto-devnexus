# -*- coding: utf-8 -*-
"""12306 车票查询 CLI（零依赖，无 key，走官网公开查询接口）。

官方没有开放平台，也没有 MCP；这里直接复用官网 otn 查询链路：
    GET /otn/leftTicket/init   -> 拿 JSESSIONID / BIGipServerotn cookie
    GET /otn/leftTicket/queryZ -> 余票（result 是 URL 编码的 | 分隔行）

用法：
    rail.py stations <关键字>                    # 查车站电报码
    rail.py query 厦门 杭州 2026-11-05            # 余票
    rail.py query 厦门北 杭州东 2026-11-05 --types G,D --limit 20
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

BASE = "https://kyfw.12306.cn"
DATA_DIR = Path(os.environ.get("RAILS_DATA_DIR") or Path.home() / ".rails")
STATION_CACHE = DATA_DIR / "stations.js"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# result 行字段下标（12306 官网固定顺序）
IDX = {
    "train_no": 2, "code": 3, "start": 4, "end": 5, "from": 6, "to": 7,
    "depart": 8, "arrive": 9, "duration": 10, "buyable": 11,
    "gr": 21, "qt": 22, "rw": 23, "rz": 24, "tz": 25, "wz": 26,
    "yw": 28, "yz": 29, "ze": 30, "zy": 31, "swz": 32,
}


def make_session():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(BASE + "/otn/leftTicket/init", headers=HEADERS)
    try:
        opener.open(req, timeout=25).read()
    except Exception as exc:
        raise SystemExit("初始化会话失败: %s" % exc)
    if not jar:
        raise SystemExit("没能拿到 12306 cookie，官网可能改了流程")
    return opener


def load_stations(refresh=False):
    """返回 {站名: 电报码}；首次拉取并缓存。"""
    text = None
    if STATION_CACHE.is_file() and not refresh:
        text = STATION_CACHE.read_text(encoding="utf-8", errors="replace")
    if not text:
        url = BASE + "/otn/resources/js/framework/station_name.js"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", "replace")
        STATION_CACHE.parent.mkdir(parents=True, exist_ok=True)
        STATION_CACHE.write_text(text, encoding="utf-8")
    table = {}
    for chunk in text.split("@"):
        parts = chunk.split("|")
        if len(parts) >= 3 and parts[1] and parts[2]:
            table[parts[1]] = parts[2]
            if len(parts) >= 5 and parts[4]:
                table.setdefault(parts[4], parts[2])   # 拼音简称也能查
    return table


def resolve(name, table):
    if name in table:
        return table[name]
    hits = [k for k in table if name in k]
    if len(hits) == 1:
        return table[hits[0]]
    if hits:
        raise SystemExit("站名不唯一：%s → 候选 %s" % (name, "、".join(hits[:8])))
    raise SystemExit("找不到车站：%s" % name)


def query(opener, from_code, to_code, date):
    qs = urllib.parse.urlencode({
        "leftTicketDTO.train_date": date,
        "leftTicketDTO.from_station": from_code,
        "leftTicketDTO.to_station": to_code,
        "purpose_codes": "ADULT",
    })
    headers = dict(HEADERS)
    headers["Referer"] = BASE + "/otn/leftTicket/init"
    headers["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(BASE + "/otn/leftTicket/queryZ?" + qs, headers=headers)
    try:
        with opener.open(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise SystemExit("查询失败 HTTP %s" % exc.code)
    if not body.lstrip().startswith("{"):
        raise SystemExit("返回的不是 JSON（被风控或需要验证码）")
    data = json.loads(body)
    if data.get("httpstatus") != 200:
        raise SystemExit("接口返回异常: %s" % data.get("messages") or data)
    rows = (data.get("data") or {}).get("result") or []
    return [urllib.parse.unquote(r).split("|") for r in rows]


def show(rows, from_code, to_code, types, limit):
    picked = []
    for f in rows:
        if len(f) < 33:
            continue
        code = f[IDX["code"]]
        prefix = code[0].upper()
        if types and prefix not in types:
            continue
        picked.append(f)
    picked.sort(key=lambda f: f[IDX["depart"]])
    if limit:
        picked = picked[:limit]
    if not picked:
        print("没有符合条件的车次。")
        return
    print("%-8s %-6s %-6s %-7s %-6s %-6s %-6s %-6s %s" %
          ("车次", "出发", "到达", "历时", "二等", "一等", "商务", "无座", "状态"))
    for f in picked:
        def cell(key):
            v = f[IDX[key]].strip()
            return v if v not in ("", "--", "无") else "-"
        status = "可订" if f[IDX["buyable"]] == "Y" else "不可订"
        print("%-8s %-6s %-6s %-7s %-6s %-6s %-6s %-6s %s" % (
            f[IDX["code"]], f[IDX["depart"]], f[IDX["arrive"]], f[IDX["duration"]],
            cell("ze"), cell("zy"), cell("swz"), cell("wz"), status))
    print("\n共 %d 趟（已按出发时间排序）" % len(picked))


def main():
    ap = argparse.ArgumentParser(description="12306 车票查询")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("stations", help="按关键字查车站电报码")
    p.add_argument("keyword")

    p = sub.add_parser("query", help="查余票")
    p.add_argument("from_station")
    p.add_argument("to_station")
    p.add_argument("date", help="YYYY-MM-DD，12306 一般只放 15 天内")
    p.add_argument("--types", default="", help="车次前缀过滤，逗号分隔，如 G,D,Z,T,K")
    p.add_argument("--limit", type=int, default=15, help="最多显示几趟，0=全部")
    args = ap.parse_args()

    table = load_stations()

    if args.cmd == "stations":
        hits = sorted({k: v for k, v in table.items() if args.keyword in k}.items())
        if not hits:
            raise SystemExit("没有匹配的车站")
        for name, code in hits[:40]:
            print("%-12s %s" % (name, code))
        return 0

    from_code = resolve(args.from_station, table)
    to_code = resolve(args.to_station, table)
    types = {t.strip().upper() for t in args.types.split(",") if t.strip()}
    started = time.time()
    opener = make_session()
    rows = query(opener, from_code, to_code, args.date)
    print("== %s(%s) → %s(%s)  %s  抓取耗时 %.1fs ==" % (
        args.from_station, from_code, args.to_station, to_code, args.date,
        time.time() - started))
    show(rows, from_code, to_code, types, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
