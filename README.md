# Auto-GitNexus

<p align="center">
  <strong>🤖 AI 驱动的 GitNexus 自动化 Skill 集合</strong>
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

Auto-GitNexus 是一套专为 Claude Code、OpenCode 等支持 MCP 的 AI 编程助手设计的 Skill 集合。它提供了全自动化的 [GitNexus](https://github.com/abhigyanpatwari/GitNexus) 部署、管理和调度能力，让你的 AI 助手能够无缝集成代码图谱检索功能。

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

---

## 🚀 快速开始

### 前置要求

- Git >= 2.0
- Node.js >= 16
- npm >= 8

### 安装

```bash
# 克隆仓库
git clone git@github.com:a574676848/auto-gitnexus.git
cd auto-gitnexus

# 确保脚本可执行
chmod +x skills/*/scripts/*.sh
```

### 使用

#### 方式一：通过 AI 助手调用（推荐）

对支持 MCP 的 AI 助手说：

> "初始化 GitNexus 环境"

或

> "使用 GitNexus 帮我生成项目架构 Wiki"

AI 助手将自动识别并执行相应的 Skill。

#### 方式二：手动执行

```bash
# 初始化 GitNexus
./skills/gitnexus-setup/scripts/gitnexus-setup.sh

# 生成 Wiki
./skills/gitnexus-wiki/scripts/gitnexus-wiki.sh
```

---

## 📚 Skill 目录

| Skill | 描述 | 触发关键词 |
|-------|------|-----------|
| [gitnexus-setup](skills/gitnexus-setup/) | 自动化安装、配置 GitNexus | "初始化 GitNexus", "配置 GitNexus", "启动 GitNexus" |
| [gitnexus-wiki](skills/gitnexus-wiki/) | 生成项目架构 Wiki | "生成 Wiki", "创建文档", "写项目文档" |

---

## 🏗️ 项目结构

```
auto-gitnexus/
├── skills/                    # Skill 集合目录
│   ├── gitnexus-setup/       # GitNexus 环境初始化 Skill
│   │   ├── SKILL.md          # Skill 定义文件（AI 调用入口）
│   │   ├── README.md         # Skill 说明文档
│   │   ├── Reference.md      # 参考资料
│   │   └── scripts/
│   │       └── gitnexus-setup.sh
│   └── gitnexus-wiki/        # GitNexus Wiki 生成器 Skill
│       ├── SKILL.md
│       ├── README.md
│       ├── Reference.md
│       └── scripts/
│           └── gitnexus-wiki.sh
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
