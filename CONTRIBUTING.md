# Contributing to Auto-GitNexus

首先，感谢你愿意为 Auto-GitNexus 做出贡献！❤️

以下是一组贡献指南，请花几分钟阅读，这将帮助我们更高效地协作。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
  - [报告 Bug](#报告-bug)
  - [建议新功能](#建议新功能)
  - [提交代码](#提交代码)
- [开发指南](#开发指南)
  - [环境设置](#环境设置)
  - [项目结构](#项目结构)
  - [提交规范](#提交规范)
- [Skill 开发规范](#skill-开发规范)

## 行为准则

本项目遵循 [Contributor Covenant](CODE_OF_CONDUCT.md) 行为准则。参与本项目即表示你同意遵守此准则。

## 如何贡献

### 报告 Bug

在提交 Bug 报告之前，请先搜索现有 issues 以避免重复。

提交 Bug 报告时，请尽可能包含以下信息：

- **问题描述**：清晰简洁地描述 Bug
- **复现步骤**：详细说明如何复现问题
- **预期行为**：描述你期望发生的行为
- **实际行为**：描述实际发生的行为
- **环境信息**：
  - 操作系统及版本
  - Git 版本
  - Node.js 版本
  - GitNexus 版本（如果已安装）
- **截图或日志**：如有相关错误日志或截图，请一并提供

### 建议新功能

我们欢迎新功能建议！请通过 GitHub Issues 提交，并包含：

- **功能描述**：清晰描述你希望添加的功能
- **使用场景**：说明这个功能将如何解决你的问题
- **可能的实现方案**：（可选）如果你有任何实现想法

### 提交代码

1. Fork 本仓库
2. 创建你的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 Pull Request

## 开发指南

### 环境设置

```bash
# 克隆仓库
git clone git@github.com:a574676848/auto-gitnexus.git
cd auto-gitnexus

# 确保脚本可执行
chmod +x skills/*/scripts/*.sh
```

### 项目结构

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
├── LICENSE                    # 许可证
├── CONTRIBUTING.md           # 本文件
├── CODE_OF_CONDUCT.md       # 行为准则
└── README.md                 # 项目主文档
```

### 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 仅文档更改
- `style:` 不影响代码含义的更改（空格、格式化等）
- `refactor:` 既不修复 Bug 也不添加功能的代码更改
- `perf:` 提升性能的代码更改
- `test:` 添加或修正测试
- `chore:` 构建过程或辅助工具的变动

示例：
```
feat: 添加对 Claude Code 配置的自动检测
fix: 修复 wiki 生成时的配置读取错误
docs: 更新 README 中的使用示例
```

## Skill 开发规范

如果你要添加新的 Skill，请遵循以下规范：

### 目录结构

```
skills/<skill-name>/
├── SKILL.md          # 必须：AI 调用入口定义
├── README.md         # 必须：用户说明文档
├── Reference.md      # 可选：技术参考资料
└── scripts/
    └── <skill-name>.sh   # 必须：核心执行脚本
```

### SKILL.md 规范

SKILL.md 是 AI 助手识别和调用 Skill 的入口文件，必须包含：

```yaml
---
name: "skill-name"
description: "简短描述，说明 Skill 的功能和触发条件"
---
```

内容结构：
1. **技能描述**：详细说明 Skill 的功能
2. **触发条件**：列出触发此 Skill 的关键词
3. **执行步骤**：清晰的执行步骤说明
4. **核心能力**：Skill 能实现的功能列表
5. **预期输出**：执行成功后的输出示例

### 脚本规范

1. **文件头**：包含脚本名称和描述
2. **错误处理**：所有命令都应包含错误处理
3. **颜色输出**：使用颜色代码提升可读性
4. **日志记录**：重要操作应记录日志
5. **权限检查**：检查并提示必要的权限

示例：
```bash
#!/bin/bash

# ==========================================
# Script: skill-name.sh
# Description: 脚本描述
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 错误处理
set -e

# 你的代码...
```

### 文档规范

- 使用中文编写文档
- 使用清晰的标题层级
- 包含代码示例
- 使用表格展示配置选项
- 提供故障排除指南

---

再次感谢你的贡献！🎉
