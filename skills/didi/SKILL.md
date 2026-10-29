---
name: didi
description: 滴滴出行。查打车价格预估、生成跳转 App 的打车链接、查询订单与司机位置、取消订单；另有地图类工具。当用户问"打车多少钱"、"叫个车"、"我的车到哪了"、"取消订单"时使用。
---

# 滴滴出行（官方 MCP，CLI 封装）

## 链路

官方只提供 MCP Server，没有独立 Skill 包。这里用手写 MCP 客户端（Streamable HTTP，零依赖）把它翻译成命令行：

```
didimcp.py --HTTPS(JSON-RPC)--> mcp.didichuxing.com --> 滴滴
```

- Key：`~/.didi\key.txt`（个人 MCP Key，控制台激活）
- 沙箱 `mcp-servers-sandbox`：**Mock 数据，不产生真实订单**
- 生产 `mcp-servers`：**产生真实订单与费用**，必须加 `--prod` 才够得着

## 用法

```bash
python skills/didi/scripts/didimcp.py tools
python ...\didimcp.py call taxi_estimate --json '{"from_lng":"118.137090","from_lat":"24.539495","from_name":"厦门高崎国际机场","to_lng":"118.073909","to_lat":"24.636977","to_name":"厦门北站"}'
python ...\didimcp.py call taxi_generate_ride_app_link --json '{...}'
python ...\didimcp.py call taxi_query_order --json '{...}'
python ...\didimcp.py --prod call taxi_create_order --json '{...}'   # 会真扣钱
```

## 13 个工具

**打车**：`taxi_estimate`（估价 + traceId）、`taxi_generate_ride_app_link`（跳 App 下单）、`taxi_create_order`（API 直接下单）、`taxi_query_order`、`taxi_cancel_order`、`taxi_get_driver_location`

**地图**：`maps_textsearch`、`maps_regeocode`、`maps_place_around`、`maps_direction_driving/transit/walking/bicycling`

## 参数（关键，踩过坑）

`taxi_estimate` 必填六项，全是**字符串**，且坐标必须来自地图工具、不能瞎编：

```
from_lng from_lat from_name to_lng to_lat to_name
```

返回里会带 **预估流程 ID（traceId）**，`taxi_generate_ride_app_link` 和 `taxi_create_order` 都要用它。车型用 `product_category` 数字：特惠快车 201 / 快车 1 / 专车 8 / 豪华车 17。

## 实测（2026-10-29，沙箱）

机场→厦门北站，估价返回：

| 车型 | 预估 | 券后 | product_category |
| --- | --- | --- | --- |
| 特惠快车 | 10 元 | 7 元 | 201 |
| 快车 | 15 元 | 10 元 | 1 |
| 专车 | 30 元 | 25 元 | 8 |
| 豪华车 | 100 元 | 85 元 | 17 |

traceId：`<DIDI_API_KEY>`

## 铁律（花钱的动作）

1. 默认只跑沙箱。`--prod` 三个字不许自己加。
2. `taxi_create_order` 会**真实下单扣费**：起点、终点、车型、预估价四项必须先摆给用户，明确说"确认"后才执行。
3. 更推荐 `taxi_generate_ride_app_link`：只生成深链，最后一脚由用户在 App 里踩，主动权在他手上。
4. 车型没指定时**必须问**，不许替他默认选快车。
5. 取消订单前先 `taxi_query_order` 看状态，避免取消费。

## 错误码

`-32002` auth failed（Key 失效）、`-32010` 缺少必填参数、`-32041` 当前状态不允许取消、`-32060` 支付失败（提示换支付方式）。

## 维护

- 换 Key：改 `data\didi\key.txt`
- 想走官方 ClawHub skill（`clawhub install didi-ride-skill-official`）需要先装 clawhub CLI，且行为等价于本脚本，非必要不引入

## 生产环境实测（2026-10-29，厦门）

`--prod taxi_estimate` 机场→厦门北站，返回 5 个车型，**沙箱的 4 个不复现**：

| 车型 | 价格 | product_category |
| --- | --- | --- |
| 惊喜特价 | 约 29 元 | 191 |
| 特惠快车 | 约 38 元 | 201 |
| 快车 | 约 39 元 | 1 |
| 专车 | 约 68 元（券后 48） | 8 |
| 六座专车 | 约 125 元（券后 100） | 9 |

- **花小猪不在车型列表里**。它是滴滴旗下独立品牌，账户与价格体系分开，滴滴 MCP 打不到；要花小猪的价只能走 App/浏览器登录态。
- 低价位用「惊喜特价 191」，比「特惠快车 201」还便宜一档，定位接近花小猪。
- 返回里带 `traceId`，有效期短；调完 `taxi_estimate` 要立刻进入确认→下单，别拖。
- `taxi_estimate` 是只读估价，不产生订单、不扣费；`taxi_create_order` 才是真花钱。

