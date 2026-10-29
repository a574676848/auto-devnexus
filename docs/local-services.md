# 本地服务接入指南

这一组 Skill 解决同一个问题：第三方服务只给你 MCP、只给你 CLI，或只给你 REST，AI 助手没法直接用。

仓库的做法是**加一层薄封装**：把官方接口翻译成本地命令行脚本，AI 助手拼参数就能调，人工也能直接跑。代价极低，收益是编辑器的 `.mcp.json` 保持干净。

- 脚本零第三方依赖，只用 Python 标准库
- 凭据只落在环境变量或用户目录，仓库内只有 `.env.example`
- 生活服务一律「只查不订 / 只查不买」

---

## 通用约定

### 凭据优先级

所有接入型 Skill 遵循同一顺序，不会静默使用兜底假值：

```text
环境变量  >  用户目录配置文件  >  报错退出
```

### 目录重定向

带脚本的接入型 Skill 都支持把凭据目录挪走，便于多账号或集中管理：

| Skill | 环境变量 | 默认位置 |
|-------|----------|----------|
| `my-coffee` | `LUCKIN_DATA_DIR` | `~/.my-coffee/` |
| `kuaidi100` | `KUAIDI100_DATA_DIR` | `~/.kuaidi100/` |
| `mijia` | `MIJIA_DATA_DIR` | `~/.mijia/` |
| `baidupan` | `BAIDUPAN_DATA_DIR` | `~/.baidupan/` |
| `amap` | `AMAP_DATA_DIR` | `~/.amap/` |
| `didi` | `DIDI_DATA_DIR` | `~/.didi/` |
| `mail` | `MAIL_DATA_DIR` | `~/.mail/` |
| `rails` | `RAILS_DATA_DIR` | `~/.rails/` |

三个例外：`fliggy` 走官方 CLI，配置固定在 `~/.flyai/`；`memos` 走官方 CLI，配置固定在 `~/.config/memos-cli/`；`cloudflare` 的配置路径由脚本内约定，不提供重定向。三者都由各自的上游工具管理位置。

### 命令写法

下文统一用 `$py` 代表脚本路径，先定义再调用：

```bash
# Linux / macOS
py=skills/kuaidi100/scripts/kd100.py && python "$py" tools

# Windows PowerShell
$py = "skills/kuaidi100/scripts/kd100.py"; python $py tools
```

MCP 类封装（`luckin.py` / `kd100.py` / `didimcp.py`）都提供同样三个动作：

- `tools`：列出该服务暴露的全部工具
- `schema <tool>`：看某个工具的入参 JSON Schema，**首次调用前必做**
- `call <tool> --json '{...}'`：按 schema 传参调用

---

## 瑞幸咖啡（my-coffee）

官方只提供 MCP，脚本 `skills/my-coffee/scripts/luckin.py` 直连其 HTTPS JSON-RPC 端点。

**申请**：瑞幸 MCP 控制台拿个人 Token。

**凭据**：`~/.my-coffee/token.txt`；读取优先级为环境变量 `LUCKIN_MCP_TOKEN`、该文件、`~/.my-coffee/LUCKIN_MCP_TOKEN`。

**命令**：

```bash
python $py tools
python $py schema previewOrder
python $py call queryShopList --json '{"longitude":118.13709,"latitude":24.539495}'
python $py call searchProductForMcp --json '{"deptId":324781,"query":"生椰拿铁"}'
python $py call previewOrder --json '{"deptId":324781,"productList":[{"amount":1,"productId":123,"skuCode":"ABC"}]}'
python $py call cancelOrder --json '{"orderId":"..."}'
```

**边界**：建单前必须先 `previewOrder` 拿到价格，确认后才允许创建；取餐码与订单状态走 `queryOrderDetailInfo`。另有一个官方 CLI `luckin`（npm 全局安装），与脚本打同一套 MCP，Token 变量名不同：`~/.luckin/.env` 里的 `LUCKIN_MCP_ORDER_TOKEN`；它默认开启自动升级，可在 `~/.luckin/config.json` 的 `updates.disable_auto_upgrade` 关闭。

---

## 快递 100（kuaidi100）

官方只提供 MCP，脚本 `skills/kuaidi100/scripts/kd100.py`。

**申请**：快递 100 开放平台申请 API Key。

**凭据**：`~/.kuaidi100/key.txt` 或环境变量 `KUAIDI100_API_KEY`。

**命令**：

```bash
python $py tools
python $py schema query_trace
python $py call query_trace --json '{"kuaidiNum":"YT1234567890","responseFormat":"markdown"}'
python $py call auto_number --json '{"kuaidiNum":"YT1234567890"}'
python $py call estimate_price --json '{"kuaidicom":"yuantong","sendAddr":"福建厦门湖里区","recAddr":"浙江杭州余杭区","weight":"1.0","responseFormat":"json"}'
python $py call estimate_time --json '{"kuaidicom":"yuantong","sendAddr":"福建厦门湖里区","recAddr":"浙江杭州余杭区"}'
```

**边界**：只查询与估价，不代下单寄件。

---

## 铁路 12306（rails）

复用官网查询链路，**不需要任何 Key**，也不需要登录。

**命令**：

```bash
python $py stations 厦门                      # 查电报码，支持模糊匹配
python $py query 厦门北 杭州东 2026-11-05      # 车次、时刻、历时、席别余票
python $py query 厦门 北京 2026-11-05 --types G,D --limit 20
```

**缓存**：车站表首次自动拉取，存 `~/.rails/stations.js`（约 200KB），之后本地读；删掉即重新拉取。

---

## 飞猪（fliggy）

飞猪有官方 AI 开放平台与官方 CLI，仓库不重复造轮子，直接约定用法。

**安装**：

```bash
npm i -g @fly-ai/flyai-cli
```

**申请**：<https://flyai.open.fliggy.com/> 控制台 →「获取 API Key」，免费，无需企业资质。

**凭据**：

```bash
flyai config set FLYAI_API_KEY "<key>"     # 写入 ~/.flyai/config.json
```

**命令**：

```bash
flyai search-flight --origin "厦门" --destination "杭州" --dep-date 2026-11-05
flyai search-flight --origin "上海" --destination "东京" --dep-date 2026-11-05 --back-date 2026-11-10 --journey-type 1 --sort-type 3
flyai search-hotel --dest-name "杭州" --poi-name "西湖" --check-in-date 2026-11-05 --check-out-date 2026-11-06 --sort price_asc
```

**坑**：Windows 下**不要用 PowerShell 管道截断输出**（`flyai ... | Select-Object -First N`）——进程提前收到 EOF 会触发 libuv 断言崩溃，数据虽完整但退出码非 0。正确姿势是先重定向到文件再读：

```powershell
flyai search-flight --origin "厦门" --destination "杭州" --dep-date 2026-11-05 2>$null > out.json
Get-Content out.json -Raw
```

---

## 滴滴出行（didi）

官方只提供 MCP，脚本 `skills/didi/scripts/didimcp.py`。

**申请**：滴滴 MCP 控制台激活个人 Key。

**凭据**：`~/.didi/key.txt`。

**命令**：

```bash
python $py tools
python $py call taxi_estimate --json '{"from_lng":"118.137090","from_lat":"24.539495","from_name":"厦门高崎国际机场","to_lng":"118.073909","to_lat":"24.636977","to_name":"厦门北站"}'
python $py call taxi_generate_ride_app_link --json '{...}'
python $py call taxi_query_order --json '{...}'
python $py --prod call taxi_create_order --json '{...}'
```

**边界**：默认沙箱环境，不产生真实订单。只有显式加 `--prod` 才会真下单扣钱，这条刻意做成必须手打，防止 AI 误触。

---

## 高德地图（amap）

高德 Web 服务 REST API，脚本 `skills/amap/scripts/amap.py`。

**申请**：<https://console.amap.com/> 创建应用，Key 绑定「Web 服务」类型。

**凭据**：`~/.amap/key.txt`。

**命令**：

```bash
python skills/amap/scripts/amap.py geo "厦门北站" --city 厦门
python skills/amap/scripts/amap.py regeo 118.073909,24.636977
python skills/amap/scripts/amap.py poi "充电桩" --city 厦门
python skills/amap/scripts/amap.py weather 厦门
```

**边界**：只做地图查询，不叫车。公交接口里那个 `taxi_cost` 字段是理论参考值，实测对该 Key 恒返回 `0`，别当报价用。

---

## 百度网盘（baidupan）

百度网盘开放平台 OAuth 2.0 授权码模式，脚本 `skills/baidupan/scripts/bdpan.py`。

**申请**：百度网盘开放平台创建应用，拿 AppKey 与 SecretKey，回调方式选 oob（授权码手动回填）。

**首次授权**（三步）：

```bash
python skills/baidupan/scripts/bdpan.py auth        # 打印授权链接，浏览器打开并扫码登录
# 从 oob 页面复制授权码，然后：
python skills/baidupan/scripts/bdpan.py token <code>
```

**凭据**：`~/.baidupan/credentials.json`（写入 access_token 与 refresh_token，脚本自动续期）。

**命令**：

```bash
python skills/baidupan/scripts/bdpan.py whoami
python skills/baidupan/scripts/bdpan.py quota
python skills/baidupan/scripts/bdpan.py ls /
python skills/baidupan/scripts/bdpan.py search 关键词
python skills/baidupan/scripts/bdpan.py refresh      # 手动刷新 token
```

---

## 米家（mijia）

米家没有开放的本地 API，仓库走 Home Assistant 加小米官方集成 `ha_xiaomi_home`，脚本只跟 HA 的 REST 接口对话。

**前置**：一台跑着 Home Assistant 的机器（本机或局域网），HA 内装好 `ha_xiaomi_home` 并登录小米账号。

**凭据**：`~/.mijia/ha.json` 存 HA 地址、管理员账号与 30 天 access_token；`~/.mijia/ha_mcp_token.txt` 存长期访问令牌（脚本实际用它，有效期 10 年）。

**命令**：

```bash
python skills/mijia/scripts/mijia.py entities --domain light
python skills/mijia/scripts/mijia.py entities --grep 主卧
python skills/mijia/scripts/mijia.py state light.example_light_a
python skills/mijia/scripts/mijia.py on  light.example_light_a
python skills/mijia/scripts/mijia.py off light.example_light_a
python skills/mijia/scripts/mijia.py service light.turn_on --entity light.example_light_b --data '{"brightness":200}'
python skills/mijia/scripts/mijia.py scenes
```

**令牌失效**：用 HA 的 WebSocket 命令 `auth/long_lived_access_token` 重新签发，覆盖 `ha_mcp_token.txt` 即可。

---

## 邮箱（mail）

标准 IMAP 读、SMTP 发，不依赖任何第三方服务。

**凭据**：`~/.mail/accounts.json`，结构参考同目录 `accounts.example.json`。QQ、163 需要用**授权码**而不是登录密码。

**命令**：

```bash
python skills/mail/scripts/mail.py accounts
python skills/mail/scripts/mail.py inbox  --account qq --limit 10
python skills/mail/scripts/mail.py inbox  --account qq --unread
python skills/mail/scripts/mail.py read   --account qq --uid 4279
python skills/mail/scripts/mail.py search --account qq --key 发票
python skills/mail/scripts/mail.py send   --account qq --to a@b.com --subject 标题 --body 正文
```

**边界**：发信是写操作，发前先确认收件人与正文。

---

## 凭据库（memos）

`memos` 是官方 CLI（memos-cli），对接 Memos v0.28 REST API。这个 Skill 的作用是统一约定「凭据存哪、怎么查」。

**凭据**：`~/.config/memos-cli/config.yaml` 存 host 与 token；环境变量 `MEMOS_PAT` 可覆盖。

**命令**：

```bash
memos auth status
memos ls
memos ls --limit 50
memos new "<内容>" --visibility PRIVATE
memos new --stdin --visibility PRIVATE        # 多行长文本从管道读
memos memo get <name>
memos rm <name>
memos api <METHOD> <PATH>                     # 原始 API 逃生口
```

**坑**：PowerShell 终端直接 `memos ls` 可能显示乱码（终端按 GBK 解码 UTF-8 所致），数据本身是正确的；用 `-j` 看 JSON 或到网页端核对。

---

## Cloudflare（cloudflare）

REST API，脚本 `skills/cloudflare/scripts/cf.py`。

**申请**：Cloudflare 控制台创建 API Token，按最小权限勾选 Zone 与 DNS 的读写。

**凭据**：`~/.cloudflare/config.json`（token、account_id、zone_id 三项），或环境变量 `CLOUDFLARE_API_TOKEN`。

**命令**：

```bash
python $py zones
python $py dns                                    # 列默认 zone 的记录
python $py dns example.com
python $py dns-add --type A --name test --content 1.2.3.4
python $py dns-add --type CNAME --name www --content example.com --proxied
python $py dns-update --id <recordId> --content 5.6.7.8
python $py dns-del --id <recordId> --yes
python $py purge --all
python $py purge --urls "https://a.com/1" "https://a.com/2"
python $py raw GET /user/tokens/verify            # 任意端点逃生口
```

**边界**：删除记录必须带 `--yes`，否则脚本直接拒绝执行；这是唯一一处刻意增加摩擦的写操作。

---

## 常见问题

**Q：脚本报 `Key not found` 或 401？**

按优先级逐层排查：环境变量是否设了空值、文件是否存在且无多余空白、Key 是否绑定了正确的服务类型（高德要选「Web 服务」，Cloudflare Token 要包含对应 Zone 权限）。

**Q：能把它当常驻服务用吗？**

不需要。这些都是「调用即走」的一次性进程，没有守护进程、没有后台端口，也正因为如此才敢说不污染你的环境。

**Q：AI 助手自动下单了怎么办？**

不会。建单与扣款类接口要么默认沙箱（滴滴），要么必须先 preview 拿价再确认（瑞幸），要么需要显式加参数（Cloudflare 删除）。把 `SKILL.md` 里的边界段交给助手读，比事后追责有用。
