# -*- coding: utf-8 -*-
"""高德地图 Web 服务 CLI（地理编码 / POI / 路径规划 / 距离 / 天气）。

注意：高德开放平台没有面向个人开发者的叫车接口，本脚本只做查询。
Key 存 ~/.amap/key.txt（可用 AMAP_DATA_DIR 覆盖）
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(os.environ.get("AMAP_DATA_DIR") or Path.home() / ".amap")
KEY_FILE = DATA_DIR / "key.txt"
BASE = "https://restapi.amap.com/v3"


def key():
    if not KEY_FILE.exists():
        raise SystemExit("缺少 %s" % KEY_FILE)
    return KEY_FILE.read_text(encoding="ascii").strip()


def call(path, **params):
    params["key"] = key()
    params["output"] = "JSON"
    url = BASE + path + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if str(data.get("status")) != "1":
        raise SystemExit("高德返回错误：info=%s infocode=%s" % (data.get("info"), data.get("infocode")))
    return data


def fmt_m(seconds):
    seconds = int(seconds or 0)
    return "%d 分钟" % round(seconds / 60)


def cmd_geo(args):
    data = call("/geocode/geo", address=args.address, city=args.city)
    if not data.get("geocodes"):
        print("没有匹配地址")
        return 0
    for item in data["geocodes"][:5]:
        print("%-46s %s  [%s]" % (item.get("formatted_address"), item.get("location"), item.get("level")))
    return 0


def cmd_regeo(args):
    data = call("/geocode/regeo", location=args.location)
    info = data.get("regeocode", {})
    print("地址: %s" % info.get("formatted_address"))
    comp = info.get("addressComponent", {})
    print("省市区: %s %s %s %s" % (comp.get("province"), comp.get("city"), comp.get("district"), comp.get("township")))
    return 0


def cmd_poi(args):
    data = call("/place/text", keywords=args.keyword, city=args.city, citylimit="true" if args.city else None, offset=10, page=1)
    pois = data.get("pois", [])
    for item in pois[:10]:
        dist = item.get("distance", "")
        print("%-38s %-28s %s %s" % (item.get("name")[:30], item.get("address", "")[:24], item.get("location"), dist))
    print("--- %d 条 ---" % len(pois))
    return 0


def cmd_around(args):
    data = call("/place/around", location=args.location, keywords=args.keyword, radius=args.radius, offset=10)
    pois = data.get("pois", [])
    for item in sorted(pois, key=lambda x: int(x.get("distance") or 0))[:10]:
        print("%-34s %-6s米 %s" % (item.get("name")[:30], item.get("distance"), item.get("address", "")[:30]))
    print("--- %d 条 ---" % len(pois))
    return 0


ROUTE_PATH = {
    "driving": "/direction/driving",
    "walking": "/direction/walking",
    "bicycling": "/direction/bicycling",
    "transit": "/direction/transit/integrated",
}


def cmd_route(args):
    data = call(ROUTE_PATH[args.mode], origin=args.origin, destination=args.destination, extensions="base", city=args.city)
    route = data.get("route", {})
    if args.mode == "transit":
        transits = route.get("transits", [])
        if not transits:
            print("没有可用公交方案：%s" % json.dumps(route, ensure_ascii=False)[:300])
            return 0
        best = transits[0]
        print("公交方案：%.1f 公里，耗时 %s，步行 %s 米，票价 %s 元，打车参考 %s 元" % (
            int(best.get("distance", 0)) / 1000.0,
            fmt_m(best.get("duration")),
            best.get("walking_distance", "?"),
            best.get("cost", "?"),
            route.get("taxi_cost", "?"),
        ))
        for seg in best.get("segments", [])[:4]:
            bus = seg.get("bus", {})
            for line in bus.get("buslines", [])[:2]:
                print("  乘坐 %s：%s → %s（%s 站）" % (
                    line.get("name"),
                    (line.get("departure_stop") or {}).get("name"),
                    (line.get("arrival_stop") or {}).get("name"),
                    line.get("via_num"),
                ))
            walk = seg.get("walking", {})
            if walk and int(walk.get("distance") or 0) > 200:
                print("  步行 %s 米" % walk.get("distance"))
        return 0
    paths = route.get("paths", [])
    if not paths:
        print("没有可用路线：%s" % json.dumps(route, ensure_ascii=False)[:300])
        return 0
    best = paths[0]
    print("%s 路线：距离 %.1f 公里，预计 %s" % (args.mode, int(best.get("distance", 0)) / 1000.0, fmt_m(best.get("duration"))))
    steps = best.get("steps", [])
    for step in steps[:6]:
        print("  %s" % step.get("instruction", "")[:80])
    if len(steps) > 6:
        print("  …共 %d 段" % len(steps))
    return 0


def cmd_dist(args):
    data = call("/distance", origins=args.origin, destination=args.destination, type=1)
    for item in data.get("results", []):
        print("直线距离 %.2f 公里，预计 %s" % (int(item.get("distance", 0)) / 1000.0, fmt_m(item.get("duration"))))
    return 0


def cmd_weather(args):
    data = call("/weather/weatherInfo", city=args.city, extensions="all")
    for f in data.get("forecasts", []):
        for cast in f.get("casts", [])[:4]:
            print("%s %s 白天%s 夜间%s %s~%s℃" % (
                f.get("city"), cast.get("date"), cast.get("dayweather"),
                cast.get("nightweather"), cast.get("nighttemp"), cast.get("daytemp")))
    return 0


def main():
    ap = argparse.ArgumentParser(description="高德地图查询 CLI（不含叫车）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("geo"); p.add_argument("address"); p.add_argument("--city"); p.set_defaults(func=cmd_geo)
    p = sub.add_parser("regeo"); p.add_argument("location"); p.set_defaults(func=cmd_regeo)
    p = sub.add_parser("poi"); p.add_argument("keyword"); p.add_argument("--city"); p.set_defaults(func=cmd_poi)
    p = sub.add_parser("around"); p.add_argument("location"); p.add_argument("--keyword"); p.add_argument("--radius", default=3000)
    p.set_defaults(func=cmd_around)
    p = sub.add_parser("route"); p.add_argument("origin"); p.add_argument("destination")
    p.add_argument("--mode", choices=list(ROUTE_PATH), default="driving"); p.add_argument("--city"); p.set_defaults(func=cmd_route)
    p = sub.add_parser("dist"); p.add_argument("origin"); p.add_argument("destination"); p.set_defaults(func=cmd_dist)
    p = sub.add_parser("weather"); p.add_argument("city"); p.set_defaults(func=cmd_weather)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
