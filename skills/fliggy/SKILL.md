---
name: fliggy
description: 飞猪旅行查询。查机票、火车票、酒店、景点门票、万豪酒店与套餐，支持关键词搜索和自然语言语义搜索，结果带真实价格与 Booking 跳转链接。当用户问"明天飞杭州多少钱""有什么酒店""这个景点门票多少""帮我规划行程"时使用。
---

# 飞猪 FlyAI（官方 CLI）

## 链路

飞猪有官方 AI 开放平台 `https://flyai.open.fliggy.com/`，提供官方 CLI（npm `@fly-ai/flyai-cli`）和官方 Skill（`alibaba-flyai/flyai-skill`）。本机已全局安装：

```
npm i -g @fly-ai/flyai-cli     # 已装
flyai <command>                # 直接用
```

- API Key：`flyai config set FLYAI_API_KEY "<key>"`，落在 `~/.flyai/config.json`
- 申请：`https://flyai.open.fliggy.com/` 控制台 →「获取 API Key」（免费，无需企业资质）
- 凭据自行保管（钥匙串 / 密码管理器 / 环境变量），不要提交进仓库
- **只查不订**：CLI 只有搜索命令，没有下单命令；每条结果给 `detailUrl`（飞猪 H5 深链），下单由用户自己在 App/网页完成

## 8 个命令

| 命令 | 用途 | 必填 |
| --- | --- | --- |
| `search-flight` | 机票（国内+国际） | `--origin` |
| `search-train` | 火车票 | `--origin` |
| `search-hotel` | 酒店 | `--dest-name` |
| `search-poi` | 景点/门票 | `--city-name` |
| `keyword-search` | 全类目关键词搜索 | `--query` |
| `ai-search` | 语义搜索（懂复杂意图） | `--query` |
| `search-marriott-hotel` | 万豪集团酒店 | `--dest-name` |
| `search-marriott-package` | 万豪酒店套餐 | `--keyword` |

### 机票

```powershell
flyai search-flight --origin "厦门" --destination "杭州" --dep-date 2026-11-05
flyai search-flight --origin "上海" --destination "东京" --dep-date 2026-11-05 --back-date 2026-11-10 --journey-type 1 --sort-type 3
```

`--journey-type`：`1` 直达 / `2` 中转。`--sort-type`：`3` 价格升序 / `4` 用时升序 / `8` 直达优先。还有 `--max-price`、`--dep-hour-start/end`、`--transport-no`。

### 酒店

```powershell
flyai search-hotel --dest-name "杭州" --poi-name "西湖" --check-in-date 2026-11-05 --check-out-date 2026-11-06 --sort price_asc
```

`--sort`：`price_asc` / `price_desc` / `distance_asc` / `rate_desc` / `no_rank`。还有 `--hotel-types`（hotel/homestay/inn）、`--hotel-bed-types`（king/twin/multi）、`--max-price`、`--key-words`。

### 返回结构

`{"data":{"itemList":[...]},"status":0,"message":"success"}`

- 机票 item：`journeys[].segments[]`（航班号、航司、起降机场/航站楼、起降时间、duration）、`ticketPrice`、`jumpUrl`
- 酒店 item：`name`、`price`（形如 `¥320`）、`star`、`address`、`interestsPoi`、`rate`、`shId`、`detailUrl`

## 硬约束

1. **只读不写**。CLI 无下单能力，别去猜 `book` 之类的命令。
2. **给链接不给承诺**。价格是查询时刻的快照，实际下单可能因库存/会员价浮动；报价格时必须说"查询时刻"。
3. **中文城市名**直接传（"厦门"、"杭州"），不需要三字码。
4. 查酒店必须同时给 `--check-in-date` 和 `--check-out-date`，否则价格没有意义。

## 已知坑（都踩过）

1. **绝不要用 PowerShell 管道截断输出**：`flyai ... | Select-Object -First N` 会让进程提前收到 EOF，触发 libuv 在 Windows 上的断言崩溃（`Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), file src\win\async.c, line 76`），数据虽完整但退出码非 0。
2. **正确姿势**：`flyai ... 2>$null > out.json`，然后 `Get-Content -Raw | ConvertFrom-Json`。少了 `2>$null` 的话，断言文本会被 `2>&1` 混进 JSON 尾部，`ConvertFrom-Json` 直接报 `Additional text encountered`。
3. **无 Key 时价格被打码**：`price` 会变成 `¥2x` 这类形式，`systemMessage` 提示"当前为体验模式"。有 Key 才是真实价格。
4. **`--hotel-stars` 实测不过滤**：传 `4,5` 仍返回经济型青旅。要筛星级得自己在结果里按 `star` 过滤。
5. `flyai --version` 不存在（会报 unknown option），别拿它做健康检查；用 `flyai --help`。
6. `price` 是带 `¥` 的字符串，比较大小要先剥符号转数字。

## 实测

2026-10-29，厦门 → 杭州 2026-11-05 机票：SC2111 06:55-08:30（95 分钟）¥300、HU7460 22:05-23:55 ¥300、MF8595 22:10-23:55 ¥330、中转经海口 ¥320。

同日杭州西湖附近酒店（无 Key）价格全是 `¥2x`；（配 Key 后）真实价格：驿客行青旅 ¥26、云租民宿 ¥27、杭州云集舍青旅 ¥28、杭州杭泰假日酒店 ¥34。
