---
name: memos
description: 密码库（Memos）。读写密钥、令牌、账号密码等敏感信息；当用户要求保存密码/Key/Token，或需要查询某个服务的凭据时使用。
---

# Memos 密码库

统一凭据仓库。**以后所有密码、密钥、令牌都写这里**，不再散落在 data/ 下的明文文件里。

## 服务

- 地址：`http://memos.example.com:52300`（**必须是 http**，52300 端口没有 TLS，用 https 会报 WRONG_VERSION_NUMBER）
- 认证：PAT `<MEMOS_PAT>`
- CLI：``memos`（已在 PATH 中）`（memos-cli，对接 Memos v0.28 REST API）
- 配置：`~/.config/memos-cli/config.yaml`（context 名 default）

## 常用命令

```bash
memos auth status                    # 验证令牌
memos ls                             # 列出备忘录（默认 10 条）
memos ls --limit 50
memos new "<内容>" --visibility PRIVATE
memos new --stdin --visibility PRIVATE   # 内容从管道读，适合多行长文本
memos memo get <name>                # 看单条，name 形如 memos/xxxx
memos rm <name>                      # 删除
memos api <METHOD> <PATH>            # 原始 API 逃生口
```

## 写入格式（统一模板）

每条一个服务，固定这几行，方便检索：

```
# <服务名>
地址/主机：<URL 或 IP>
账号：<username>
密码/Key：<secret>
用途：<哪个 skill 在用>
备注：<坑、有效期、限制>
```

示例（已入库的 7 条）：
米家/HA、服务器 SSH、百度网盘、QQ 邮箱、高德地图、滴滴 MCP、Memos 自身。

## 检索约定

- `memos ls | Select-String 关键字` 可按服务名模糊找
- 已知会涉及的服务：米家、百度网盘、QQ邮箱、高德、滴滴、GitLab、TokenRhythm、金叶云

## 坑

- PowerShell 终端直接 `memos ls` 会显示乱码（终端 GBK 解码 UTF-8 所致），**数据本身是正确的**，网页端或 `-j` 输出正常
- `-j` 要放在子命令前：`memos -j ls`，写在后面会报 unrecognized arguments
- 内容里含中文和换行时，用单引号 here-string 传，别用双引号
- 备忘录默认 visibility 用 PRIVATE，不要设 PUBLIC

## 安全边界

- 读凭据属于敏感操作，只在当前任务确实需要时读，不要批量导出
- 写入前确认服务名和字段完整，写错要 `memos rm` 后重写
- 不在对话里复述完整密钥，需要时给前 4 位 + 后 4 位
