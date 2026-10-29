# Auto-Devnexus

<p align="center">
  <strong>给 AI 编程助手补上「手和脚」——22 个可直接落地的 Skill 集合</strong>
</p>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  </a>
  <a href="#-快速开始">
    <img src="https://img.shields.io/badge/Quick%20Start-5%20minutes-brightgreen" alt="Quick Start">
  </a>
  <img src="https://img.shields.io/badge/Skills-22-blueviolet" alt="22 Skills">
  <img src="https://img.shields.io/badge/Python-3.6%2B-3776AB" alt="Python 3.6+">
</p>

---

## 📖 项目简介

Auto-Devnexus 是一套面向 AI 编程助手的 **Skill 集合**。每个 Skill 是一份 `SKILL.md` 定义加一组可执行脚本，AI 助手读完说明就能调用，不需要你手工拼命令。

它解决两类具体问题：

1. **工程侧缺能力**：代码图谱、仓库解析、工单流转、测试编排、界面取证、文档体系，这些能力主流 AI 助手并不自带。
2. **第三方服务难接**：瑞幸、快递100、12306、飞猪、滴滴、高德、百度网盘、米家、邮箱、Cloudflare 这类服务，官方只给 MCP、只给 CLI，或只给 REST。仓库把它们统一翻译成本地命令行脚本——**不向你编辑器的 `.mcp.json` 注入任何配置**，零第三方依赖，凭据只留在本机。

设计取舍只有一条：**能用一个标准库脚本解决的，就不引入框架、常驻进程或全局 MCP 配置。** 需要长期驻留的只有 GitNexus 的图谱服务，其余全部是「调用即走」的一次性进程。

### 什么是 GitNexus？

[GitNexus](https://github.com/abhigyanpatwari/GitNexus) 是一个代码库分析工具，能：

- 🔍 解析 Git 仓库，生成 AST 与调用图谱
- 🌐 提供本地 HTTP 图谱微服务
- 📝 调用 LLM 生成项目架构 Wiki
- 🔗 通过 MCP 协议与 AI 助手集成

本仓库的 `gitnexus-setup` 与 `gitnexus-wiki` 两个 Skill 负责它的安装、索引、钩子与 Wiki 生成。

### 什么是 Skill？

Skill 是一种 AI 可识别的自动化脚本集合：`SKILL.md` 用 frontmatter 声明触发条件，正文写清执行步骤与边界，脚本放在同目录的 `scripts/` 下。AI 助手按需加载，人工也能直接跑。

---

## 🗂 目录

- [项目简介](#-项目简介)
- [能力一览](#-能力一览)
- [快速开始](#-快速开始)
- [凭据与安全约定](#-凭据与安全约定)
- [通用脚本](#-通用脚本)
- [项目结构](#️-项目结构)
- [文档导航](#-文档导航)
- [开发与贡献](#️-开发与贡献)
- [许可证](#-许可证)
- [致谢](#-致谢)

---

## ✨ 能力一览

22 个 Skill，按用途分组；点击名称进入各自的 `SKILL.md`。

### 工程与研发

| Skill | 能力 | 依赖 |
|-------|------|------|
| [gitnexus-setup](skills/gitnexus-setup/) | 自动安装 GitNexus、后台建图谱、注入 MCP 配置、挂 `post-commit` 钩子、起 54321 端口 Web UI | Node.js / npm |
| [gitnexus-wiki](skills/gitnexus-wiki/) | 读取 LLM 配置，异步生成项目架构 Wiki 到 `.gitnexus/wiki/` | Node.js / LLM API Key |
| [codebase-memory-mcp-setup](skills/codebase-memory-mcp-setup/) | 跨平台安装、迁移、增强 Codebase Memory MCP（CBM），配置 graph-first 主导模式与 auto_index | Node.js |
| [jira-integration](skills/jira-integration/) | Jira 工单查询、创建、更新、流转、删除、评论与工时（针对 Jira Server 7.5.2 的 v2 API） | Python 标准库 |
| [repo-parser](skills/repo-parser/) | 解析 GitHub 与私有 Git 仓库源码，三级凭证策略加分块深度阅读，防上下文超载 | Python 标准库 |
| [dev-test](skills/dev-test/) | 测试统一入口，路由到用例编写、冒烟、集成 / e2e、UI 视觉、bug 回归与增量测试等 8 个子手册 | 无 |
| [cdp-control](skills/cdp-control/) | 用 Chrome DevTools Protocol 驱动并取证 WebView2 / Tauri / Electron / Chrome / 无头 Chromium | Python 标准库 |

### 文档、设计与检索

| Skill | 能力 | 依赖 |
|-------|------|------|
| [open-source-docs](skills/open-source-docs/) | 开源项目文档建设方法论：README 门面、docs 信息架构、命名纠偏、中文友好化 | 无 |
| [frontend-ui-ux](skills/frontend-ui-ux/) | 全栈前端与 UI/UX 系统：视觉 Token、高阶微动效、高转化落地页、Image-to-Code、品牌全案 | 无 |
| [image-generation](skills/image-generation/) | 按 `config.toml` 声明的图像模型生成或编辑图片 | Python 标准库 + 模型 Key |
| [web-search](skills/web-search/) | 四路并行搜索与抓取（Bing RSS / AnySearch / TinyFish / Tavily），跨源去重后按共识排序 | Python 标准库 + 各源 Key |

### 本地服务接入

这一组的共同约定：脚本零第三方依赖，凭据不入库，生活服务一律「只查不订 / 只查不买」。细则见 [docs/local-services.md](docs/local-services.md)。

| Skill | 能力 | 接入形态 |
|-------|------|----------|
| [my-coffee](skills/my-coffee/) | 瑞幸咖啡：查门店、搜商品、预览建单、订单与取餐码、取消订单 | 官方 MCP 转 `luckin.py` |
| [kuaidi100](skills/kuaidi100/) | 快递100：实时轨迹、快递公司识别、运费与时效预估 | 官方 MCP 转 `kd100.py` |
| [didi](skills/didi/) | 滴滴出行：打车估价、跳转 App 下单链接、订单与司机位置、取消订单 | 官方 MCP 转 `didimcp.py`（默认沙箱） |
| [fliggy](skills/fliggy/) | 飞猪：机票、火车票、酒店、景点门票、万豪酒店与套餐 | 官方 CLI `@fly-ai/flyai-cli` |
| [rails](skills/rails/) | 铁路 12306：车次、时刻、历时与席别余票 | 复用官网查询链路，无需 Key |
| [amap](skills/amap/) | 高德地图：地理编码、POI 与周边、路径规划、距离、天气 | Web 服务 REST API |
| [baidupan](skills/baidupan/) | 百度网盘：账号信息、容量、列目录、搜索、取下载直链 | 开放平台 OAuth 2.0 加 REST |
| [mijia](skills/mijia/) | 米家智能家居：读实体状态、开关灯、执行场景 | Home Assistant REST API |
| [mail](skills/mail/) | 邮箱：IMAP 读信与检索、SMTP 发信，QQ / 163 / Gmail 多账号 | IMAP 与 SMTP |
| [memos](skills/memos/) | 凭据库：按服务存取密码、Key、Token | 官方 CLI `memos-cli` |
| [cloudflare](skills/cloudflare/) | Cloudflare：域名与 DNS 增删改、缓存清理、任意 API 调用 | REST API 转 `cf.py` |

---

## 🚀 快速开始

### 1. 前置要求

- **Git** >= 2.0
- **Python** >= 3.6（Jira 集成与全部本地服务脚本；除 Jira 外均为标准库实现，**无需 pip 安装任何依赖**）
- **Node.js** >= 16 / **npm** >= 8（GitNexus 两个 Skill，以及飞猪官方 CLI）
- **PowerShell** 5.1+ 或 7（仅 Windows 下的 WezTerm 脚本需要）

可选外部 CLI，按需安装：

```bash
npm i -g gitnexus                 # gitnexus-setup / gitnexus-wiki
npm i -g @fly-ai/flyai-cli        # fliggy
# memos 由 memos-cli 提供，装好后执行 memos auth status 验证
```

### 2. 安装

```bash
git clone git@github.com:a574676848/auto-devnexus.git
cd auto-devnexus
```

Linux / macOS 下为两个 Shell 脚本补执行权限：

```bash
chmod +x skills/*/scripts/*.sh
```

Python 脚本无需安装步骤，`python skills/<skill>/scripts/<script>.py --help` 即可查看子命令。Windows 上如 `python` 未进 PATH，用 `py` 代替。

### 3. 验证

挑一个不依赖任何 Key 的 Skill 试跑：

```bash
python skills/rails/scripts/rail.py stations 厦门
```

能打印出车站电报码表即说明环境就绪。

### 4. 调用方式

**方式一：交给 AI 助手（推荐）**

对支持 Skill / MCP 的助手直接说人话，它会自行加载对应 `SKILL.md`：

> "初始化 GitNexus 环境"
> "用 GitNexus 帮我生成项目架构 Wiki"
> "帮我在 Jira 创建一个工单"
> "查一下我有没有杭州到厦门的余票"
> "把主卧的灯关掉"

**方式二：手动执行**

```bash
# GitNexus 环境初始化与 Wiki
./skills/gitnexus-setup/scripts/gitnexus-setup.sh
./skills/gitnexus-wiki/scripts/gitnexus-wiki.sh

# Jira
python skills/jira-integration/scripts_py/auth.py --domain "https://jira.example.com" --user "<账号>" --token "<Token>"
python skills/jira-integration/scripts_py/search.py --jql "assignee = currentUser() AND status = 'Open'"

# 仓库解析
python skills/repo-parser/scripts/parse_github.py https://github.com/user/repo --workdir ./parse-out

# 本地服务（示例）
python skills/amap/scripts/amap.py geo "厦门北站" --city 厦门
python skills/cloudflare/scripts/cf.py zones
python skills/kuaidi100/scripts/kd100.py tools
```

每个 Skill 的完整命令集见其 `SKILL.md`，本地服务类见 [docs/local-services.md](docs/local-services.md)。

---

## 🔐 凭据与安全约定

接入类 Skill 一律遵守三条：

1. **不写进仓库**：凭据只放环境变量或用户目录下的配置文件，仓库内只留 `.env.example` 与 `.gitignore` 规则。
2. **读取有优先级**：环境变量优先于用户目录配置文件，两者都没有时报错退出，不静默使用兜底假值。
3. **可重定向**：每个 Skill 都支持对应的 `*_DATA_DIR` 环境变量，把凭据目录挪到你想放的位置。

| 技能 | 环境变量 | 本地凭据文件 |
|------|----------|--------------|
| `my-coffee` | `LUCKIN_MCP_TOKEN` | `~/.my-coffee/token.txt`（另有 `~/.my-coffee/LUCKIN_MCP_TOKEN` 兜底；官方 `luckin` CLI 读 `~/.luckin/.env` 的 `LUCKIN_MCP_ORDER_TOKEN`） |
| `kuaidi100` | `KUAIDI100_API_KEY` | `~/.kuaidi100/key.txt` |
| `fliggy` | `FLYAI_API_KEY` | `~/.flyai/config.json`（由 `flyai config set` 写入） |
| `cloudflare` | `CLOUDFLARE_API_TOKEN` | `~/.cloudflare/config.json` |
| `mijia` | — | `~/.mijia/ha.json`（HA 地址与账号）加 `~/.mijia/ha_mcp_token.txt`（长期访问令牌） |
| `baidupan` | — | `~/.baidupan/credentials.json` |
| `amap` | — | `~/.amap/key.txt` |
| `didi` | — | `~/.didi/key.txt` |
| `mail` | — | `~/.mail/accounts.json` |
| `memos` | `MEMOS_PAT` | `~/.config/memos-cli/config.yaml` |
| `rails` | `RAILS_DATA_DIR` | `~/.rails/stations.js`（站名缓存，可随时删除） |

上述文件、`.env` 与 `__pycache__/` 均已列入 `.gitignore`。若你 fork 后新增凭据文件，请同步补规则。

**能力边界**：生活服务类 Skill 默认「只查不订、只查不买」，下单与支付动作留给官方 App；涉及金额的接口必须先预估价再进入下一步，绝不自动扣款。滴滴脚本默认走沙箱，`--prod` 需显式指定。

---

## 📦 通用脚本

| 目录 | 说明 |
|------|------|
| [scripts/windows/wezterm/](scripts/windows/wezterm/) | Windows 下 WezTerm 的一键安装、配置重置、图片粘贴处理与缓存清理。优先 `winget`，失败回退 GitHub MSI；覆盖配置前自动备份并只保留最近 5 份 |

```powershell
.\scripts\windows\wezterm\install-wezterm.bat
```

详见 [docs/windows-wezterm.md](docs/windows-wezterm.md)。

---

## 🏗️ 项目结构

```text
auto-devnexus/
├── skills/                     # 22 个 Skill，每个都是 SKILL.md 加可选 scripts/ 的自包含目录
│   ├── gitnexus-setup/         # 代码图谱：环境初始化
│   ├── gitnexus-wiki/          # 代码图谱：架构 Wiki 生成
│   ├── codebase-memory-mcp-setup/  # CBM 安装与维护
│   ├── jira-integration/       # Jira 工单（scripts_py/）
│   ├── repo-parser/            # 仓库源码解析（scripts/）
│   ├── dev-test/               # 测试路由入口加 8 个子手册 AGENT.md
│   ├── cdp-control/            # Chromium 界面驱动与取证（references/ 附协议速查）
│   ├── open-source-docs/       # 文档建设方法论（Reference.md 附模板与检查清单）
│   ├── frontend-ui-ux/         # 前端与设计系统（references/ 共 9 篇）
│   ├── image-generation/       # 图像生成（config.toml 声明模型）
│   ├── web-search/             # 四路并行搜索（.env 配置各源 Key）
│   ├── my-coffee/  kuaidi100/  didi/                 # 官方 MCP 转本地 CLI 封装
│   ├── fliggy/  memos/                               # 官方 CLI 封装
│   ├── rails/  amap/  baidupan/  mijia/  mail/  cloudflare/   # 官网链路 / REST / IMAP
│   └── ...                     # 每个目录内的 SKILL.md 是唯一权威说明
├── scripts/windows/wezterm/    # 通用 Windows 自动化脚本
├── docs/                       # 文档中心（索引见 docs/README.md）
├── .github/                    # Issue 模板、PR 模板、CI
├── CONTRIBUTING.md             # 贡献指南
├── CODE_OF_CONDUCT.md          # 行为准则
└── LICENSE                     # MIT
```

---

## 📖 文档导航

| 文档 | 内容 |
|------|------|
| [docs/README.md](docs/README.md) | 文档中心索引，按「入门 / 接入 / 规范 / 排障」分流 |
| [docs/getting-started.md](docs/getting-started.md) | 从零到第一次成功调用：环境检查、安装、两种调用方式、常见故障 |
| [docs/local-services.md](docs/local-services.md) | 11 个本地服务接入的申请入口、凭据配置、命令速查与能力边界 |
| [docs/skill-specification.md](docs/skill-specification.md) | Skill 的目录结构、`SKILL.md` 字段规范、脚本与输出约定 |
| [docs/windows-wezterm.md](docs/windows-wezterm.md) | WezTerm 一键安装脚本的目录位置、生成文件与备份策略 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 分支、提交、PR 与新增 Skill 的流程 |

---

## 🛠️ 开发与贡献

### 添加新 Skill

1. 在 `skills/` 下新建目录，名称用小写短横线（如 `my-skill`）
2. 按 [docs/skill-specification.md](docs/skill-specification.md) 编写 `SKILL.md` 与 `scripts/`
3. 脚本优先用 Python 标准库；确需第三方依赖时在 `SKILL.md` 中写清安装命令
4. 凭据一律走环境变量或用户目录，并在根 `.gitignore` 补对应规则
5. 更新 [README 的能力一览](#-能力一览) 与 [docs/local-services.md](docs/local-services.md)（接入类）
6. 提交 Pull Request，CI 会做基础校验

详细流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 贡献

欢迎一切形式的贡献：报告 Bug、建议新功能、改进文档、提交代码。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 🙏 致谢

- [GitNexus](https://github.com/abhigyanpatwari/GitNexus) — 代码图谱分析能力
- [Claude Code](https://github.com/anthropics/claude-code) — AI 编程助手
- [OpenCode](https://github.com/opencode-ai/opencode) — 开源 AI 编程助手

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/a574676848">Alex.ZBG</a>
</p>
