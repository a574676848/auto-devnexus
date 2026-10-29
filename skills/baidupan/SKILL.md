---
name: baidupan
description: 查询与管理百度网盘。通过百度网盘开放平台 OAuth 2.0 + REST API 读取账号信息、容量、列目录、搜索文件、取下载直链。当用户提到百度网盘、网盘、云盘、查网盘空间、找网盘里的文件、网盘下载链接时使用。
---

# 百度网盘

## 链路

```
本机脚本 --HTTPS--> openapi.baidu.com(OAuth) / pan.baidu.com(REST) --> 百度网盘
```

- 应用：AppID `<BAIDU_APP_ID>`，scope `basic,netdisk`
- 凭据目录：`~/.baidupan\credentials.json`
  - `api_key` / `secret_key` / `app_id`
  - `access_token`：30 天有效（2592000 秒），过期自动用 `refresh_token` 续
- 账号：baidu_name `<YOUR_BAIDU_ACCOUNT>`，uk `<YOUR_BAIDU_UK>`，vip_type 0（普通用户）

## 用法

```bash
python skills/baidupan/scripts/bdpan.py whoami
python skills/baidupan/scripts/bdpan.py quota
python skills/baidupan/scripts/bdpan.py ls /
python skills/baidupan/scripts/bdpan.py ls /照片
python skills/baidupan/scripts/bdpan.py search 关键词
python skills/baidupan/scripts/bdpan.py refresh
```

授权（仅首次或 token 彻底失效）：

```bash
python .../bdpan.py auth            # 打印授权链接，浏览器打开并用百度账号扫码登录
python .../bdpan.py token <code>    # 把 oob 页面给出的授权码换成 token
```

## 实测基线（2026-10-29）

- 容量：total `2205465706496` 字节 ≈ 2.005 TB，used `73714492130` ≈ 68.6 GB
- 根目录：`apps`、`K2刷机工具包`、`【瑞客论坛…】300分钟搞定算法`、`尚硅谷谷粒学院项目视频教程`、`我的资源`、`五月天-自传`、`薛之谦`、`照片`，另有一个 `月圆之夜_v1.5.9.5解锁dlc金币(无需断网).apk`（约 348 MB）

## 接口口径与限制

- 普通用户走 xpan 接口，单次 `ls` 建议 limit≤1000，目录深了要翻页（`start` 参数）
- 下载直链接口 `filemetas` 必须带 `User-Agent: pan.baidu.com`，否则返回 403；直链有时效，拿到就立刻用
- 非会员下载会被限速，这是账号侧策略，不是脚本问题
- **分享类接口（创建分享链接、转存）不对个人开发者开放**，别承诺能做分享
- `errno=-6` = 鉴权失败，通常是 token 过期或 scope 没带 `netdisk`；先 `refresh` 再试
- `errno=2`/`31066` 等业务错误按官方 errno 表查，不要把网络错误当成文件不存在

## 安全边界

- 读取、列目录、搜索、取直链：可以直接做
- 删除、移动、重命名、覆盖上传：属于破坏性操作，必须先说清楚路径与后果，用户确认后再执行
- 不主动上传本地敏感文件到网盘

## 维护

- token 存 `credentials.json`，`expires_at` 是 Unix 秒；脚本会在剩余不足 5 分钟时自动刷新
- 彻底失效（refresh 也报错）就重跑 `auth` + `token`
- 应用信息在百度网盘开放平台控制台可查：https://pan.baidu.com/union/
