---
name: cloudflare
description: Cloudflare 管理。查域名与 DNS 记录、增删改解析、清理缓存，以及任意 Cloudflare API 的原始调用。当用户提到 Cloudflare、CF、DNS 解析、加条 A 记录、改 CNAME、清缓存、域名为什么没生效时使用。
---

# Cloudflare（REST API + 脚本）

## 为什么不走 MCP

Cloudflare 有官方托管 MCP（`https://mcp.cloudflare.com/mcp`，支持 OAuth 或 API Token 当 Bearer），但官方自己算过账：

| 方式 | 工具数 | Token 开销 |
| --- | --- | --- |
| 原生 MCP（完整 schema） | 2594 | ~1,170,000 |
| 原生 MCP（仅必填参数） | 2594 | ~244,000 |
| Code Mode（官方缓解方案） | 2 | ~1,000 |

把 2594 个端点全暴露成工具，光 schema 就超过大多数模型上下文。所以这里直接打 REST API，一个脚本搞定。

## 链路

- 脚本：`skills\cloudflare\scripts\cf.py`（零依赖 urllib）
- 凭据：`data\cloudflare\config.json` → `{"token","account_id","default_zone"}`
- 也认环境变量 `CLOUDFLARE_API_TOKEN`（优先级更高）
- API 基址：`https://api.cloudflare.com/client/v4`
- Token 申请：`https://dash.cloudflare.com/profile/api-tokens` → Create Custom Token

## 用法

```powershell
$py = "skills/cloudflare/scripts/cf.py"

python $py zones                                   # 列域名
python $py dns                                     # 列默认 zone 的记录
python $py dns example.com                       # 指定 zone

python $py dns-add --type A --name test --content 1.2.3.4
python $py dns-add --type CNAME --name www --content example.com --proxied

python $py dns-update --id <recordId> --content 5.6.7.8
python $py dns-update --id <recordId> --proxied
python $py dns-update --id <recordId> --no-proxied

python $py dns-del --id <recordId> --yes           # 不加 --yes 会被拒绝

python $py purge --all                             # 清全站缓存
python $py purge --urls "https://a.com/1" "https://a.com/2"

python $py raw GET /user/tokens/verify             # 逃生口：任意端点
python $py raw GET "/zones/<zid>/settings"
```

`zone` 参数可以省略（用配置里的 `default_zone`），也可以直接传 32 位 zone id。

## 铁律

1. **删除 DNS、改 NS、purge 全站、删 Zone 一律先报后做**。这几类不可逆或直接影响线上，先说清影响面再动手。
2. `dns-del` 硬性要求 `--yes`，这是故意的护栏，别为了省事直接加。
3. **`ddns.example.com` 是自建密码库的对外入口**（`http://ddns.example.com:52300`），proxy 关着、直连 203.0.113.11。这条记录一旦改坏，凭据库就打不开了——动它之前必须单独确认。
4. 改解析后不要立刻断言生效，DNS 有 TTL 缓存；验证用 `nslookup 名字 1.1.1.1`。
5. 清缓存只影响已被橙云代理（`proxied=true`）的记录，灰云记录没有缓存可清。

## 已知坑

1. **开启了 Client IP Address Filtering 的 Token 用不了 MCP**（Cloudflare 明确不支持），但对本脚本的 REST 调用没影响——所以脚本路线反而更宽容。
2. 账号级 Token 想自动识别 account_id，需要带 `Account → Account Resources → Read` 权限。
3. `POST /zones/{id}/dns_records` 的 `ttl=1` 表示「自动」，不是 1 秒。
4. `purge_everything` 是一次性全清，没有撤回；有 CDN 命中率要求的站点慎用。
5. 列表接口有 `per_page` 上限（DNS 记录最多 100/页），域名多了要翻页。

## 实测（2026-10-29）

- Token `<CLOUDFLARE_API_TOKEN>` 状态 active，到期 2027-10-29 15:59:59Z
- Account：`<CLOUDFLARE_ACCOUNT_ID>`（<YOUR_EMAIL>'s Account）
- Zone：`example.com` → `<CLOUDFLARE_ZONE_ID>`，status=active
- DNS 6 条：
  - A `cf-sg.example.com` → 203.0.113.10（橙云）
  - A `ddns.example.com` → 203.0.113.11（灰云，密码库入口）
  - A `jinye.example.com` → 203.0.113.12（灰云）
  - CNAME `speed.example.com` → cf-sg.example.com（橙云）
  - TXT `_acme-challenge.speed` / `_cf-custom-hostname.speed`（证书验证用）
