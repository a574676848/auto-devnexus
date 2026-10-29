---
name: kuaidi100
description: 快递100 查快递。按单号查实时物流轨迹、自动识别快递公司、预估运费与送达时效。当用户问"我的快递到哪了""帮我看下这个单号""寄这个要多少钱""几天能到"时使用。
---

# 快递100（官方 MCP，CLI 封装）

## 链路

官方 MCP Server（`kuaidi100-api/kuaidi100-MCP`），Streamable HTTP，key 拼在 URL 上：

```
https://api.kuaidi100.com/mcp/streamable?key=<KUAIDI100_API_KEY>
```

本 skill 用零依赖手写 MCP 客户端把它翻译成命令行，不往 Axon 注入 MCP 配置。

- 脚本：`skills\kuaidi100\scripts\kd100.py`
- Key：`~/.kuaidi100/key.txt`（优先级：环境变量 `KUAIDI100_API_KEY` > 该文件）
- 申请页：https://api.kuaidi100.com/ （注册送 100 单）
- 凭据（key / customer / secret / userid）自行保管，不要提交进仓库
- server=`kuaidi100-mcp`，工具 5 个

## 用法

```powershell
$py = "skills/kuaidi100/scripts/kd100.py"

python $py tools                    # 列工具
python $py schema query_trace       # 看入参 schema（首次必做）

# 查轨迹（最常用）
python $py call query_trace --json '{"kuaidiNum":"YT1234567890","responseFormat":"markdown"}'

# 不确定哪家快递：先识别
python $py call auto_number --json '{"kuaidiNum":"YT1234567890"}'

# 运费预估
python $py call estimate_price --json '{"kuaidicom":"yuantong","sendAddr":"福建厦门湖里区","recAddr":"浙江杭州余杭区","weight":"1.0","responseFormat":"json"}'

# 时效预估
python $py call estimate_time --json '{"kuaidicom":"yuantong","sendAddr":"福建厦门湖里区","recAddr":"浙江杭州余杭区"}'
```

## 5 个工具的关键参数

| 工具 | 必填 | 说明 |
| --- | --- | --- |
| `query_trace` | `kuaidiNum` | 查实时轨迹；**顺丰速运 / 顺丰快运 / 中通必须再传 `phone`**（收件人手机号） |
| `auto_number` | `kuaidiNum` | 按单号猜快递公司，返回候选列表 |
| `estimate_price` | `kuaidicom`、`sendAddr`、`recAddr`、`weight` | 运费预估，重量单位 kg（字符串，如 `"1.0"`） |
| `estimate_time` | 快递公司编码 + 收寄地址 + 下单时间 + 业务类型 | 发货前时效预估 |
| `estimate_time_with_logistic` | 同上 + 历史轨迹 | 在途时效预估 |

`kuaidicom` 只支持这 8 家：`shunfeng` `jd` `debangkuaidi` `yuantong` `zhongtong` `shentong` `yunda` `ems`

所有工具都接受 `key: null`（不用填，鉴权已在 URL）和 `responseFormat: json|markdown`（默认 markdown）。

## 汇报格式（给用户看）

查轨迹时按这个顺序讲，不要贴原始 JSON：

1. 一句话现状：已签收 / 派送中 / 运输中 / 已揽收
2. 最近 2–3 个节点：时间 + 地点 + 动作
3. 预计送达（接口给了才说）
4. 异常要主动点出来：长时间无更新、退回、疑难件

## 费用与配额

- 按单扣费，注册送 100 单
- **同一运单号 40 天内重复查询不重复扣费**，所以反复问「到哪了」不会掉额度
- 运费预估和时效预估各扣各自品类的单量，和轨迹查询分开计

## 已知坑

1. key 在 URL query 上，不是 Authorization header，别照抄其他 MCP 的写法
2. `weight` 是字符串不是数字，传 `1.0` 而不是 `1`
3. 顺丰/中通不传 `phone` 会查不出来，不是接口坏了
4. `estimate_price` 是「寄件参考价」，真要下单寄件得用 `order_price`，两者报价可能不一致
5. 请求头必须带 `Accept: application/json, text/event-stream`

## 实测

2026-10-29，`estimate_price`：圆通 `yuantong`，福建厦门湖里区 → 浙江杭州余杭区，1.0kg → **圆通普快 ¥12.0**。`tools/list` 返回 server=kuaidi100-mcp，5 个工具。
