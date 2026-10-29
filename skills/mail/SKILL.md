---
name: mail
description: 收发与管理邮箱。通过 IMAP/SMTP 读取收件箱、按关键词检索、读正文、发送邮件，支持 QQ / 网易 / Gmail 多账号。当用户提到邮箱、收件箱、查邮件、有没有新邮件、发邮件、回邮件、找某封邮件时使用。
---

# 邮箱（IMAP / SMTP）

## 已接入

| 账号名 | 地址 | 状态 |
| --- | --- | --- |
| `qq` | <YOUR_QQ_EMAIL> | ✅ 已验证（读写双向通） |
| `163` | <YOUR_163_EMAIL> | ✅ 已验证（收件箱可读，6 封实测） |
| `gmail` | <YOUR_GMAIL_EMAIL> | ✅ 已验证（收件箱可读，8 封实测） |

配置：`~/.mail\accounts.json`（模板 `accounts.example.json`）

## 用法

```bash
python skills/mail/scripts/mail.py accounts
python ...\mail.py inbox   --account qq --limit 10
python ...\mail.py inbox   --account qq --unread
python ...\mail.py read    --account qq --uid 4279
python ...\mail.py search  --account qq --key 发票
python ...\mail.py send    --account qq --to a@b.com --subject 标题 --body 正文
```

零依赖（imaplib / smtplib / email 标准库），任何 Python 3 都能跑。

客户端配置供参考（QQ 邮箱 / 企业邮箱同理）：
- IMAP `imap.qq.com:993` SSL
- SMTP `smtp.qq.com:465` SSL
- 密码填**授权码**，不是 QQ 登录密码

## 实测记录（2026-10-29）

- IMAP 登录成功，收件箱能正常列出（uid 4273–4279）
- SMTP 自发一封「Axon 邮件通道验证」，约 20 秒后 uid=4279 到达收件箱，发件人、主题、时间都对
- QQ 邮箱自发信有 10–30 秒延迟，不是失败

## 限制与坑

- QQ 邮箱普通账号 IMAP 只同步最近 30 天邮件，VIP 邮箱不受此限（当前账号是 VIP）
- 只读打开（`readonly=True`），阅读**不会**把邮件标记为已读；要标记已读得手动改
- 脚本目前只支持纯文本正文，**不支持附件**；需要发附件时先说明，再扩展
- 邮件正文按 text/plain 优先；纯 HTML 邮件会取不到内容（可后续补 HTML 转文本）
- 单账号发信频率受 QQ 侧限制，别拿它做群发
- **邮件头 charset 可能是 `unknown-8bit`**（Gmail 收到的第三方营销信常见），不是合法编码名，直接 `decode()` 会抛 `LookupError` 把整个列表打断。`decode()` 已改成经 `_safe_decode()` 逐级回退（原 charset → utf-8 → gb18030 → latin-1）
- Gmail 走 IMAP/SMTP 而非 Gmail API，看不到标签体系；国内网络偶有抖动，失败重试一次即可
- Gmail 必须用**应用专用密码**（16 位，去掉空格），前提是账号已开两步验证；普通登录密码一定失败
- **网易系（163/126/yeah.net）登录后必须先发 IMAP ID 命令**，否则 `SELECT` 返回 `Unsafe Login. Please contact kefu@188.com`。脚本里 `imap_conn()` 已按域名自动发送，别删。163 的授权码要先去网页端「设置 → POP3/SMTP/IMAP」开启服务（需短信验证）再生成

## 安全边界

- 读、列、搜：直接做
- **发信是对外不可撤回动作**：收件人、主题、正文必须先给用户过目，明确同意后才发；一次只发一封
- 不自动回复、不自动转发、不批量群发
- 不把邮件正文里的验证码、密码、密钥写进任何日志或记忆

## 维护

- 新增账号：在 `accounts.json` 里加一段，key 自定义（如 `163`），填 address/授权码/服务器
- 授权码失效（`imaplib.IMAP4.error: Login fail`）：重新去邮箱后台生成
- 网易邮箱需要在网页端开启 IMAP/SMTP 服务并生成「客户端授权密码」；Gmail 需要开两步验证后用「应用专用密码」
