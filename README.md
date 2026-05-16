# Auto-Devnexus

<p align="center">
  <strong>🤖 AI 驱动的 devnexus 自动化 Skill 集合</strong>
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

Auto-devnexus 是一套专为 Claude Code、OpenCode 等支持 MCP 的 AI 编程助手设计的 Skill 集合。它提供了全自动化的 [devnexus](https://github.com/abhigyanpatwari/devnexus) 部署、管理和调度能力，让你的 AI 助手能够无缝集成代码图谱检索功能。

### 什么是 devnexus？

devnexus 是一个强大的代码库分析工具，能够：
- 🔍 解析 Git 仓库，生成 AST 与调用图谱
- 🌐 提供本地 HTTP 图谱微服务
- 📝 调用 LLM 生成项目架构 Wiki
- 🔗 通过 MCP 协议与 AI 助手集成

### 什么是 Skill？

Skill 是一种 AI 可识别的自动化脚本集合，通过标准化的 `SKILL.md` 文件定义触发条件和执行逻辑，让 AI 助手能够自主调用复杂的自动化任务。

---

## ✨ 功能特性

### 🔧 devnexus 环境初始化 (`devnexus-setup`)

- **自动全局安装**：检测并安装 npm 包 `devnexus`
- **异步图谱构建**：后台运行 `devnexus analyze` 生成 AST 索引
- **MCP 配置注入**：自动注册图谱检索工具到 AI 助手
- **自动同步钩子**：挂载 `post-commit` 钩子实现代码提交后自动更新
- **守护进程管理**：进程防抖（防冲突）、全异步非阻塞执行
- **定制化高位端口**：使用 `54321` 端口避免冲突

### 📝 devnexus Wiki 生成器 (`devnexus-wiki`)

- **智能层级读取**：优先读取 `~/.devnexus/config.json` → OpenCode 配置 → Claude Code 配置
- **全局持久化**：新配置保存到 `~/.devnexus/config.json`，后续使用无需重复输入
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

## 🚀 快速开始

### 前置要求

- Git >= 2.0
- Node.js >= 16 (仅 devnexus 相关技能需要)
- npm >= 8 (仅 devnexus 相关技能需要)
- Python >= 3.6 (仅 Jira 集成技能需要)

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

> "初始化 devnexus 环境"

或

> "使用 devnexus 帮我生成项目架构 Wiki"

或

> "帮我在 Jira 创建一个工单"

或

> "查询 Jira 中我的待办工单"

AI 助手将自动识别并执行相应的 Skill。

#### 方式二：手动执行

```bash
# 初始化 devnexus
./skills/devnexus-setup/scripts/devnexus-setup.sh

# 生成 Wiki
./skills/devnexus-wiki/scripts/devnexus-wiki.sh

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
| [devnexus-setup](skills/devnexus-setup/) | 自动化安装、配置 devnexus | "初始化 devnexus", "配置 devnexus", "启动 devnexus" |
| [devnexus-wiki](skills/devnexus-wiki/) | 生成项目架构 Wiki | "生成 Wiki", "创建文档", "写项目文档" |
| [jira-integration](skills/jira-integration/) | Jira 工单管理集成 | "Jira", "工单", "创建工单", "查询工单", "更新工单" |
| [repo-parser](skills/repo-parser/) | 仓库源码解析，支持 GitHub 及私有仓库 | "解析仓库", "读取代码", "查看仓库结构" |
| [open-source-docs](skills/open-source-docs/) | 开源项目文档建设，重构 README、docs、示例说明与命名纠偏 | "重写 README", "整理 docs", "最佳开源项目文档", "中文友好化文档" |

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
│   ├── devnexus-setup/       # devnexus 环境初始化 Skill
│   │   ├── SKILL.md          # Skill 定义文件（AI 调用入口）
│   │   ├── README.md         # Skill 说明文档
│   │   ├── Reference.md      # 参考资料
│   │   └── scripts/
│   │       └── devnexus-setup.sh
│   ├── devnexus-wiki/        # devnexus Wiki 生成器 Skill
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── Reference.md
│   │   └── scripts/
│   │       └── devnexus-wiki.sh
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

- [devnexus](https://github.com/abhigyanpatwari/devnexus) - 提供强大的代码图谱分析能力
- [Claude Code](https://github.com/anthropics/claude-code) - AI 编程助手
- [OpenCode](https://github.com/opencode-ai/opencode) - 开源 AI 编程助手

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/a574676848">Alex.ZBG</a>
</p>
