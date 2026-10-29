---
name: my-coffee
description: 瑞幸咖啡下单助手。查门店、搜商品、预览与创建自提订单、查订单/取餐码、取消订单。当用户提到瑞幸、luckin、点杯咖啡、拿铁、美式、生椰拿铁、橙C美式、果茶、轻乳茶、取餐码、订单状态、取消订单时使用。
---

# 瑞幸咖啡（官方 MCP，CLI 封装）

## 链路

官方 my-coffee Skill 是 `instructionOnly`，本体不含可执行代码，只声明依赖 MCP Server。MCP 端点是 Streamable HTTP：

```
https://gwmcp.lkcoffee.com/order/user/mcp
Authorization: Bearer ${LUCKIN_MCP_TOKEN}
```

本 skill 用零依赖手写 MCP 客户端把它翻译成命令行，**不往 Axon 注入 MCP 配置**（避免污染 .mcp.json）：

```
luckin.py --HTTPS(JSON-RPC)--> gwmcp.lkcoffee.com --> 瑞幸
```

- 脚本：`skills\my-coffee\scripts\luckin.py`
- Token：`~/.my-coffee/token.txt`（读取优先级：环境变量 `LUCKIN_MCP_TOKEN` > 该文件 > `~/.my-coffee/LUCKIN_MCP_TOKEN`）
- Token 申请页：https://open.lkcoffee.com/mcp （登录后创建）
- 凭据请放进系统钥匙串或密码管理器，不要提交进仓库；需要展示时只给首 4 位与末 4 位
- 官方原始包（SKILL.md / manifest.json / CHANGELOG）不随本仓库分发，请自行从申请页获取

## 用法

```powershell
$py = "skills/my-coffee/scripts/luckin.py"

python $py tools                                    # 列工具（8 个）
python $py schema previewOrder                      # 看入参 schema（首次调用前必做）
python $py call queryShopList --json '{"longitude":118.13709,"latitude":24.539495}'
python $py call searchProductForMcp --json '{"deptId":324781,"query":"生椰拿铁"}'
python $py call previewOrder --json '{"deptId":324781,"productList":[{"amount":1,"productId":123,"skuCode":"ABC"}]}'
python $py call queryOrderDetailInfo --json '{"orderId":"..."}'
python $py call cancelOrder --json '{"orderId":"..."}'
```

8 个工具：`queryShopList`、`searchProductForMcp`、`switchProduct`、`queryProductDetailInfo`、`previewOrder`、`createOrder`、`queryOrderDetailInfo`、`cancelOrder`。

## 官方 CLI（可选，已装）

`luckin 0.0.1` 已装到 `%LOCALAPPDATA%\.luckin\bin\luckin.exe`，并写入用户 PATH（新开终端才生效）。打的是同一套 MCP，返回与 `luckin.py` 完全一致：

```powershell
luckin store <纬度> <经度> [门店名]
luckin menu / luckin product / luckin order / luckin mcp list
luckin version
```

- Token 走 `~/.luckin/.env` 的 `LUCKIN_MCP_ORDER_TOKEN`（**变量名和 MCP 官方的 `LUCKIN_MCP_TOKEN` 不同**），已写入同一枚 token
- `luckin login` 走浏览器登录刷新 token；`luckin logout` 清除
- 该 CLI 默认开启自动升级，改 `~/.luckin/config.json` 的 `updates.disable_auto_upgrade` 关掉
- 默认仍用 `luckin.py`：字段可控、无自升级、不需要常驻 12MB 二进制；要人读格式或新子命令时再上官方 CLI

## 下单硬约束（按序执行，不许跳步）

1. **Schema 优先**：调工具前先 `schema <tool>`，以真实 schema 为准。
2. **门店**：`queryShopList` 必传经纬度（即使传了 `deptName`），列出前 5 家让用户确认，不许默认选最近那家。确认后记住 `deptId` + 门店坐标 + 名称 + 地址。
3. **商品**：`searchProductForMcp` 固定 `delivery=pick`，必传 `deptId`、`query`。涉及杯型/温度/糖度/奶基等定制，必须先 `queryProductDetailInfo` 看可选属性，再 `switchProduct` 换 SKU，不许凭搜索结果猜 SKU。
4. **一次确认**：建单前只确认一次——门店名/地址/营业时间、商品名/规格/数量、预估价。明确告知「确认后先 previewOrder 拿最终价；若应付不高于预估、明细一致、优惠正常，就直接建单出二维码」。
5. **预览**：必须 `previewOrder`，不许直接 `createOrder`。`totalInitialPrice` 订单价、`privilegeMoney` 减免、`discountPrice` 应付。`couponCodeList` 非空时，建单必须原样透传。
6. **建单**：`createOrder` 传 `deptId`、`productList`、门店经纬度、`couponCodeList`。
7. **价格判断**：应付 ≤ 预估且明细一致且优惠正常 → 直接建单，不再二次确认；否则停下再请用户确认。单位不明就停，不自行换算。

## 支付与信息边界

- 只展示 `payOrderQrCodeUrl`：Markdown 图片 `![支付二维码](完整URL)` + 可点击链接 `[打开支付二维码](完整URL)`。禁止展示 `payOrderUrl`。URL 不许截断。
- 生成的是**真实支付二维码**，扫码即扣款。绝不自动支付、绝不代扫。
- 未支付前，不提取餐码/可取餐/预计取餐。
- 回复给：订单号、门店、商品、数量、价格、减免、应付（金额统一加 `¥`）。
- 建单成功后追加：`支付完成后告诉我一声，我可以马上帮你查询订单状态和取餐码。` + `1. 已支付，帮我查取餐码` / `2. 还没支付，稍后再查`。

## 其他规则

- 外送/配送/外卖/送到 → 统一回：`目前仅支持到店自取哦，您同意去门店自提吗？\n1. 同意\n2. 不同意`，同意后继续自提流程。
- 距离：只在拿到用户给的准确经纬度时才展示，IP 粗定位不显示距离。
- 缺参只追问一个必要信息，不并发追问。
- 不展示工具调用痕迹：工具名、命令、JSON/SSE 原始返回、报错堆栈一律只内部消化。
- 定位：本机可信，可用 `curl -s https://ipinfo.io/json` 取 `loc`（"纬度,经度"）做城市级粗定位；失败或要精确位置就问用户。

## 已知坑

1. 请求头必须带 `Accept: application/json, text/event-stream`，少了网关直接 400。
2. 服务端走 SSE，响应要按 `data:` 事件解析（脚本已处理）。
3. 真实调用必须用完整 token；`oauth validate failed` + Authorization 形如 `***`/`…` 就是被脱敏了。
4. 只看 `searchProductForMcp` 的 `estimatePrice` 会错，最终价格必须 `previewOrder`。
5. `createOrder` 只给商品名不够，必须 `productId` + `skuCode`。
6. 取消未支付订单后如需重下，要重新走完整流程（新订单号）。

## 实测

2026-10-29 厦门高崎机场坐标（118.13709, 24.539495）查询门店：返回 8 家，最近「航空商务广场店」0.6064 km，营业中。`server=luckyordermcpmaster`，工具 8 个。
