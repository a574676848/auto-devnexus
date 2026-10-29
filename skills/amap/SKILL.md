---
name: amap
description: 高德地图查询。地理编码、逆地理、POI 搜索与周边、驾车/步行/骑行/公交路线、距离测量、天气预报。当用户问"从 A 到 B 多远/多久"、"附近有什么"、"这个地址在哪"、"明天天气"时使用。
---

# 高德地图（只做查询，不能叫车）

## 先说死这条边界

**高德开放平台没有面向个人开发者的叫车/打车接口。** 服务目录只有地图渲染、地理编码、POI、路径规划、交通态势、天气。

- ❌ 不能下单叫车、不能派单、不能支付
- ⚠️ 公交接口里有个 `taxi_cost` 字段，那是理论打车价的参考值，实测对这个 Key 返回 `0`，**不要当报价用**
- ✅ 能算距离和耗时，用来估算"打车大概要多久、"这段路值不值得叫车"

要真的叫车，只能是滴滴/美团那条线，且要企业资质。

## 链路

- 高德 Web 服务 Key：`~/.amap\key.txt`
- 应用名 `axon`，绑定服务 Web服务，控制台 https://console.amap.com/
- 脚本走 `https://restapi.amap.com/v3`，零依赖

## 用法

```bash
python skills/amap/scripts/amap.py geo "厦门北站" --city 厦门
python ...\amap.py regeo 118.073909,24.636977
python ...\amap.py poi "充电桩" --city 厦门
python ...\amap.py around 118.137090,24.539495 --keyword 加油站 --radius 3000
python ...\amap.py route 118.137090,24.539495 118.073909,24.636977 --mode driving
python ...\amap.py route ... --mode transit --city 厦门
python ...\amap.py dist 118.137090,24.539495 118.073909,24.636977
python ...\amap.py weather 厦门
```

`--mode` 可选 `driving` / `walking` / `bicycling` / `transit`。

注意：`route` 的起终点必须是 **经纬度**（`lng,lat`），不是地址。地址先用 `geo` 转。

## 实测基线（2026-10-29，厦门）

```
geo 厦门北站            → 118.073909,24.636977
geo 高崎国际机场         → 118.137090,24.539495
route 机场→北站 driving → 17.3 公里，23 分钟，14 段
route 同段 transit       → 17.5 公里，68 分钟，步行 1676 米，票价 15 元
around 机场 3km 加油站   → 7 条，最近 1947 米
weather 厦门             → 晴，21~27℃
dist 同段                → 直线 17.23 公里
```

## 限制与坑

- 坐标是 **GCJ-02**（火星坐标），不是 GPS 的 WGS-84；和别的服务混用要先转换，否则差几百米
- `geo` 会返回多个候选（检票口、出入口这类），列表第一条通常最合适，必要时让人确认
- 公交方案 `transit` 必须带 `--city`
- Key 有日配额（个人免费额度约每天几千次），批量循环调用要节制
- 错误码看 `infocode`：`10001` Key 失效、`10003` 超配额、`10009` Key 与服务不匹配

## 安全边界

- 纯查询，不产生费用，不涉及账号
- 查的是公共地理数据，没有隐私风险；但**不要**把家庭住址、常去地点批量导出或外发

## 维护

- 换 Key：改 `data\amap\key.txt` 一行即可
- 控制台可查配额：https://console.amap.com/dev/key/app
