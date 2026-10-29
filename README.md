# Auto-Devnexus

<p align="center">
  <strong>🤖 AI 驱动的 Auto-Devnexus 自动化 Skill 集合</strong>
</p>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  </a>
  <a href="#快速开始">
    <img src="https://img.shields.io/badge/Quick%20Start-5%20minutes-brightgreen" alt="Quick Start">
  </a>
</p>

---
## 📖 简介

Auto-devnexus 是一套专为 Claude Code、OpenCode 等支持 MCP 的 AI 编程助手设计的 Skill 集合。它提供了全自动化的 [GitNexus](https://github.com/abhigyanpatwari/GitNexus) 部署、管理和调度能力，让你的 AI 助手能够无缝集成代码图谱检索功能。

除代码图谱能力外，仓库还收纳了一组「官方 MCP / CLI / REST 的轻薄封装」技能：把瑞幸咖啡、快递100、12306、飞猪、滴滴、高德、百度网盘、米家、邮箱、Cloudflare 这类日常服务翻译成本地命令行脚本，AI 助手无需注入额外 MCP 配置即可调用，凭据一律留在本机、不进仓库。

### 什么是 GitNexus？

GitNexus 是一个强大的代码库分析工具，能够：
- 🔍 解析 Git 仓库，生成 AST 与调用图谱
- 🌐 提供本地 HTTP 图谱微服务
- 📝 调用 LLM 生成项目架构 Wiki
- 🔗 通过 MCP 协议与 AI 助手集成

### 什么是 Skill？

Skill 是一种 AI 可识别的自动化脚本集合，通过标准化的 `SKILL.md` 文件定义触发条件和执行逻辑，让 AI 助手能够自主调用复杂的自动化任务。

---

## ✨ 功能特性

### 🔧 GitNexus 环境初始化 (`gitnexus-setup`)

- **自动全局安装**：检测并安装 npm 包 `gitnexus`
- **异步图谱构建**：后台运行 `gitnexus analyze` 生成 AST 索引
- **MCP 配置注入**：自动注册图谱检索工具到 AI 助手
- **自动同步钩子**：挂载 `post-commit` 钩子实现代码提交后自动更新
- **守护进程管理**：进程防抖（防冲突）、全异步非阻塞执行
- **定制化高位端口**：使用 `54321` 端口避免冲突

### 📝 GitNexus Wiki 生成器 (`gitnexus-wiki`)

- **智能层级读取**：优先读取 `~/.gitnexus/config.json` → OpenCode 配置 → Claude Code 配置
- **全局持久化**：新配置保存到 `~/.gitnexus/config.json`，后续使用无需重复输入
- **进程防抖**：杀掉旧的 wiki 进程，避免资源冲突
- **异步执行**：后台生成文档，不阻塞用户操作
- **多模型支持**：支持 OpenAI、Anthropic 及兼容接口

### 📋 Jira 集成 (`jira-integration`)

- **零依赖**：纯 Python 3 实现，无需额外安装依赖
- **Jira Server 7.5.2 优化**：专门适配 v2 API
- **完整工单操作**：支持查询、创建、更新、流转和删除工单
- **智能打单**：两阶段机制，先获取 schema 再提交
- **多层认知记忆**：内置 MEMORY.md 系统，持续学习和进化
- **安全认证**：支持密码和 API Token 认证
- **评论查询**：支持读取工单评论，便于排查问题闭环

### 🔍 仓库解析 (`repo-parser`)

- **多源解析**：支持 GitHub（公开/私有）和 GitLab/Gitea/内网等私有仓库
- **智能凭证管理**：三级递进凭证策略（集成插件 → 本地缓存 → 用户手动提供），凭证缓存至 `%USERPROFILE%\.repo-parser\`
- **分块深度阅读**：自动检测项目类型，过滤无关文件，分卷切分代码输出，防止上下文超载
- **目录与执行分离**：脚本在技能目录，代码 clone 和输出在执行目录，通过 `--workdir` 参数控制

### 🪟 Windows WezTerm 自动化脚本

- **一键安装**：自动检测 WezTerm 是否已安装，未安装时优先使用 `winget`，失败后回退 GitHub MSI 静默安装
- **幂等执行**：重复执行时跳过安装，仅重置用户目录中的 WezTerm 配置与辅助脚本
- **自动备份**：覆盖 `wezterm.lua` 之前自动备份旧配置，只保留最近 5 份
- **图片粘贴增强**：提供剪贴板图片落盘脚本，配合 `wezterm.lua` 支持智能粘贴
- **缓存清理**：自动清理 `%TEMP%\WezTerm_Images` 中超过 1 天的旧图片

---

### 🔌 本地服务接入系列（官方 MCP / CLI / REST 封装）

官方只提供 MCP、只提供 CLI，或压根没有 SDK 的服务，统一翻译成本地命令行：脚本零第三方依赖，不往 AI 助手的 `.mcp.json` 注入配置，凭据只留在环境变量或用户目录。

- **`my-coffee`**：瑞幸咖啡下单 —— 查门店、搜商品、查 SKU 明细、预览建单、订单与取餐码、取消订单（官方 MCP → `luckin.py`）
- **`kuaidi100`**：快递100 —— 实时轨迹、快递公司识别、运费与时效预估（官方 MCP → `kd100.py`）
- **`rails`**：铁路 12306 —— 车次、时刻、历时与席别余票，复用官网查询链路，无需 Key
- **`fliggy`**：飞猪 —— 机票、火车票、酒店、门票、万豪酒店与套餐搜索（官方 CLI `@fly-ai/flyai-cli`）
- **`didi`**：滴滴出行 —— 打车估价、跳转 App 下单链接、订单与司机位置、取消订单（官方 MCP → `didimcp.py`，默认沙箱）
- **`amap`**：高德地图 —— 地理编码、POI 与周边、路径规划、距离与天气（Web 服务 REST API，只查不叫车）
- **`baidupan`**：百度网盘 —— 账号信息、容量、列目录、搜索、取下载直链（开放平台 OAuth 2.0 + REST API）
- **`mijia`**：米家智能家居 —— 通过 Home Assistant 读实体状态、开关灯、执行场景（HA REST API → `mijia.py`）
- **`mail`**：邮箱 —— IMAP 读信与检索、SMTP 发信，多账号（QQ / 163 / Gmail）
- **`memos`**：凭据库 —— 按服务存取密码 / Key / Token（Memos CLI 封装）
- **`cloudflare`**：Cloudflare —— 域名与 DNS 记录增删改、缓存清理与任意 API 调用（REST API → `cf.py`）

> 生活服务类技能默认「只查不订 / 只查不买」，下单动作留给用户在官方 App 完成；涉及支付的操作一律先预览价格，绝不自动扣款。

---

## 🚀 快速开始

### 前置要求

- Git >= 2.0
- Node.js >= 16 (仅 GitNexus 相关技能需要)
- npm >= 8 (仅 GitNexus 相关技能需要)
- Python >= 3.6 (仅 Jira 集成技能需要)

### 凭据约定

接入类技能不把凭据写进仓库：优先读环境变量，其次读用户目录下的配置文件（各技能均支持对应的 `*_DATA_DIR` 环境变量覆盖目录）。

| 技能 | 环境变量 | 本地凭据文件 |
|------|----------|--------------|
| `my-coffee` | `LUCKIN_MCP_TOKEN` | `~/.my-coffee/token.txt` |
| `kuaidi100` | `KUAIDI100_API_KEY` | `~/.kuaidi100/key.txt` |
| `fliggy` | `FLYAI_API_KEY` | `~/.flyai/config.json`（由 `flyai config set` 写入） |
| `cloudflare` | `CLOUDFLARE_API_TOKEN` | `~/.cloudflare/config.json` |
| `mijia` | — | `~/.mijia/ha.json` + `~/.mijia/ha_mcp_token.txt` |
| `baidupan` | — | `~/.baidupan/credentials.json` |
| `amap` | — | `~/.amap/key.txt` |
| `didi` | — | `~/.didi/key.txt` |
| `mail` | — | `~/.mail/accounts.json` |
| `memos` | `MEMOS_PAT` | `~/.config/memos-cli/config.yaml` |
| `rails` | 无需 Key | `~/.rails/stations.js`（站名缓存） |

上述本地文件与 `__pycache__` 均已列入 `.gitignore`。

### 安装

```bash
# 克隆仓库
git clone git@github.com:a574676848/auto-devnexus.git
cd auto-devnexus

# 确保脚本可执行
chmod +x skills/*/scripts/*.sh
```

Windows 用户如需安装 WezTerm，可直接执行：

```powershell
.\scripts\windows\wezterm\install-wezterm.bat
```

### 使用

#### 方式一：通过 AI 助手调用（推荐）

对支持 MCP 的 AI 助手说：

> "初始化 GitNexus 环境"

或

> "使用 GitNexus 帮我生成项目架构 Wiki"

或

> "帮我在 Jira 创建一个工单"

或

> "查询 Jira 中我的待办工单"

AI 助手将自动识别并执行相应的 Skill。

#### 方式二：手动执行

```bash
# 初始化 GitNexus
./skills/gitnexus-setup/scripts/gitnexus-setup.sh

# 生成 Wiki
./skills/gitnexus-wiki/scripts/gitnexus-wiki.sh

# Jira 集成（Python 脚本）
python skills/jira-integration/scripts_py/auth.py --domain "<Jira域名>" --user "<账号>" --token "<密码/Token>"
python skills/jira-integration/scripts_py/search.py --jql "assignee = currentUser() AND status = 'Open'"
```

Windows WezTerm 安装：

```powershell
.\scripts\windows\wezterm\install-wezterm.bat
```

执行后会自动生成：

```text
%USERPROFILE%\.config\wezterm\wezterm.lua
%USERPROFILE%\.wezterm_cleanup.bat
%USERPROFILE%\.wezterm_cleanup.ps1
%USERPROFILE%\.wezterm_img_handler.ps1
```

详细说明见 [docs/windows-wezterm.md](docs/windows-wezterm.md)。

---

## 📚 Skill 目录

| Skill | 描述 | 触发关键词 |
|-------|------|-----------|
| [gitnexus-setup](skills/gitnexus-setup/) | 自动化安装、配置 GitNexus | "初始化 GitNexus", "配置 GitNexus", "启动 GitNexus" |
| [gitnexus-wiki](skills/gitnexus-wiki/) | 生成项目架构 Wiki | "生成 Wiki", "创建文档", "写项目文档" |
| [codebase-memory-mcp-setup](skills/codebase-memory-mcp-setup/) | 跨平台安装、迁移、配置与维护 Codebase Memory MCP（CBM） | "安装 CBM", "配置 MCP", "CBM 索引", "graph-first", "auto_index" |
| [jira-integration](skills/jira-integration/) | Jira 工单管理集成 | "Jira", "工单", "创建工单", "查询工单", "更新工单" |
| [repo-parser](skills/repo-parser/) | 仓库源码解析，支持 GitHub 及私有仓库 | "解析仓库", "读取代码", "查看仓库结构" |
| [open-source-docs](skills/open-source-docs/) | 开源项目文档建设，重构 README、docs、示例说明与命名纠偏 | "重写 README", "整理 docs", "最佳开源项目文档", "中文友好化文档" |
| [frontend-ui-ux](skills/frontend-ui-ux/) | 专家级一体化前端与 UI/UX 系统，含全栈架构、高阶微动效、视觉 Token 刻度、高转化落地页、设计转动态展演（MP4/GIF）、Image-to-Code 与品牌全案 | "前端", "UI/UX", "设计系统", "微动效", "落地页", "动效展演", "Image-to-Code", "品牌" |
| [image-generation](skills/image-generation/) | 调用配置文件中声明的图像模型生成或编辑图片 | "生成图片", "画图", "编辑图片", "gpt-image-2", "z-image-turbo" |
| [dev-test](skills/dev-test/) | 测试统一入口：写用例、冒烟、集成/e2e、UI 视觉、bug 回归与增量测试 | "测试", "写用例", "冒烟", "集成测试", "e2e", "bug 回归", "覆盖矩阵" |
| [web-search](skills/web-search/) | 四路并行 web 搜索（Bing RSS / AnySearch / TinyFish / Tavily），跨源去重与共识排序 | "搜索", "联网", "查资料", "web search", "fact-check", "调研" |
| [cdp-control](skills/cdp-control/) | 用 Chrome DevTools Protocol 驱动并取证任意 Chromium 内核界面（WebView2 / Tauri / Electron / Chrome / 无头），纯标准库零依赖、跨平台 | "CDP", "真机验证", "桌面端验证", "点击", "输入", "截图取证", "remote-debugging-port", "DevTools 协议" |

| [my-coffee](skills/my-coffee/) | 瑞幸咖啡下单：门店、商品与 SKU、预览建单、订单与取餐码、取消订单（官方 MCP 的 CLI 封装） | "瑞幸", "点杯咖啡", "生椰拿铁", "取餐码", "取消订单" |
| [kuaidi100](skills/kuaidi100/) | 快递100 查快递：实时轨迹、快递公司识别、运费与时效预估（官方 MCP 的 CLI 封装） | "快递到哪了", "查单号", "寄件多少钱", "几天能到" |
| [rails](skills/rails/) | 铁路 12306 余票查询：车次、时刻、历时与席别余票（复用官网查询链路，无需 Key） | "有没有票", "几点的车", "还有座吗" |
| [fliggy](skills/fliggy/) | 飞猪旅行查询：机票、火车票、酒店、门票、万豪酒店与套餐（官方 CLI） | "飞杭州多少钱", "有什么酒店", "门票多少", "规划行程" |
| [didi](skills/didi/) | 滴滴出行：打车估价、跳转 App 下单链接、订单与司机位置、取消订单（官方 MCP 的 CLI 封装） | "打车多少钱", "叫个车", "车到哪了", "取消订单" |
| [amap](skills/amap/) | 高德地图查询：地理编码、POI 与周边、路径规划、距离、天气（Web 服务 API） | "从 A 到 B 多远", "附近有什么", "这个地址在哪", "明天天气" |
| [baidupan](skills/baidupan/) | 百度网盘：账号信息、容量、列目录、搜索文件、取下载直链（开放平台 OAuth 2.0） | "百度网盘", "网盘空间", "找网盘里的文件", "下载直链" |
| [mijia](skills/mijia/) | 米家智能家居：通过 Home Assistant 读状态、开关灯、执行场景（HA REST API） | "米家", "小爱", "把主卧灯关掉", "智能家居状态" |
| [mail](skills/mail/) | 邮箱收发：IMAP 读信与检索、SMTP 发信，多账号（QQ / 163 / Gmail） | "查邮件", "有没有新邮件", "发邮件", "找某封邮件" |
| [memos](skills/memos/) | 凭据库读写：按服务存取密码 / Key / Token（Memos CLI 封装） | "存密码", "查某个服务的 Key", "凭据库" |
| [cloudflare](skills/cloudflare/) | Cloudflare 管理：域名/DNS 增删改、缓存清理与任意 API 调用（零依赖脚本） | "Cloudflare", "加条 A 记录", "改 CNAME", "清缓存" |

## 📦 通用脚本

| 目录 | 描述 |
|------|------|
| [scripts/windows/wezterm/](scripts/windows/wezterm/) | Windows 下 WezTerm 的安装、配置重置、图片处理与缓存清理脚本 |

---

## 🏗️ 项目结构

```
auto-devnexus/
├── scripts/                   # 通用自动化脚本
│   └── windows/
│       └── wezterm/
│           ├── install-wezterm.bat
│           ├── install-wezterm.ps1
│           ├── cleanup-wezterm.bat
│           ├── cleanup-wezterm.ps1
│           ├── wezterm-img-handler.ps1
│           └── templates/
│               └── wezterm.lua
├── skills/                    # Skill 集合目录
│   ├── gitnexus-setup/       # GitNexus 环境初始化 Skill
│   │   ├── SKILL.md          # Skill 定义文件（AI 调用入口）
│   │   ├── README.md         # Skill 说明文档
│   │   ├── Reference.md      # 参考资料
│   │   └── scripts/
│   │       └── gitnexus-setup.sh
│   ├── gitnexus-wiki/        # GitNexus Wiki 生成器 Skill
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── Reference.md
│   │   └── scripts/
│   │       └── gitnexus-wiki.sh
│   └── jira-integration/     # Jira 集成 Skill
│       ├── SKILL.md          # Skill 定义文件
│       ├── MEMORY.md         # 多层认知记忆系统
│       └── scripts_py/       # Python 脚本目录
│           ├── auth.py       # 身份认证
│           ├── create.py     # 创建工单
│           ├── delete.py     # 删除工单
│           ├── get_issue.py  # 获取工单详情
│           ├── schema.py     # 获取工单 schema
│           ├── search.py     # 查询工单
│           ├── transition.py # 工单状态流转
│           ├── update.py     # 更新工单
│           └── utils.py      # 工具函数
│   ├── repo-parser/          # 仓库解析 Skill
│       ├── SKILL.md          # Skill 定义文件
│       ├── README.md         # Skill 说明文档
│       └── scripts/
│           ├── parse_github.py      # GitHub 仓库解析
│           ├── parse_local_git.py   # 私有仓库解析
│           └── repo_common.py       # 共用模块（凭证管理、解析逻辑）
│   └── open-source-docs/     # 开源项目文档建设 Skill
│       ├── SKILL.md          # Skill 定义文件
│       ├── README.md         # Skill 说明文档
│       └── Reference.md      # 文档方法论、模板与检查清单
├── docs/                      # 项目文档
├── .github/                   # GitHub 配置
│   └── workflows/            # CI/CD 工作流
├── LICENSE                    # MIT 许可证
├── CONTRIBUTING.md           # 贡献指南
├── CODE_OF_CONDUCT.md       # 行为准则
└── README.md                 # 本文件
```

---

## 🛠️ 开发

### 添加新 Skill

1. 在 `skills/` 目录下创建新目录
2. 按照 [Skill 开发规范](CONTRIBUTING.md#skill-开发规范) 创建必要文件
3. 更新本 README 的 Skill 目录表格
4. 提交 Pull Request

详细规范请参考 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 🤝 贡献

我们欢迎所有形式的贡献！

- 🐛 报告 Bug
- 💡 建议新功能
- 📝 改进文档
- 🔧 提交代码

请参考 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细指南。

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 🙏 致谢

- [GitNexus](https://github.com/abhigyanpatwari/GitNexus) - 提供强大的代码图谱分析能力
- [Claude Code](https://github.com/anthropics/claude-code) - AI 编程助手
- [OpenCode](https://github.com/opencode-ai/opencode) - 开源 AI 编程助手

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/a574676848">Alex.ZBG</a>
</p>
