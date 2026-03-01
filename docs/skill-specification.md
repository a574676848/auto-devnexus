# Skill 规范文档

本文档定义了 Auto-GitNexus 中 Skill 的开发规范和标准。

## 什么是 Skill？

Skill 是一种 AI 可识别的自动化脚本集合，通过标准化的 `SKILL.md` 文件定义触发条件和执行逻辑，让 AI 助手能够自主调用复杂的自动化任务。

## Skill 目录结构

每个 Skill 必须遵循以下目录结构：

```
skills/<skill-name>/
├── SKILL.md              # 必须：AI 调用入口定义
├── README.md             # 必须：用户说明文档
├── Reference.md          # 可选：技术参考资料
└── scripts/
    └── <skill-name>.sh   # 必须：核心执行脚本
```

## 文件规范

### SKILL.md

SKILL.md 是 AI 助手识别和调用 Skill 的入口文件，必须包含 YAML Front Matter 和 Markdown 内容。

#### YAML Front Matter

```yaml
---
name: "skill-name"                          # Skill 标识名（小写，短横线连接）
description: "简短描述，说明功能和触发条件"    # 50-150 字符
---
```

#### 内容结构

```markdown
# Skill 标题

## 技能描述

详细说明 Skill 的功能、用途和工作原理。

## 触发条件

当用户说出以下关键词时调用此 Skill：
- "关键词1"
- "关键词2"
- "关键词3"

## 执行步骤

### 1. 步骤名称
具体操作说明：
```bash
./scripts/skill-name.sh
```

### 2. 错误处理
如果遇到 "Permission denied" 错误：
```bash
chmod +x ./scripts/skill-name.sh
```

## 核心能力

1. **能力1**：描述
2. **能力2**：描述
3. **能力3**：描述

## 预期输出

执行成功后，向用户展示：
- 输出项1
- 输出项2
```

### README.md

README.md 面向最终用户，应该包含：

1. **简介**：Skill 的功能概述
2. **功能特性**：功能列表
3. **目录结构**：文件说明
4. **快速使用**：使用示例
5. **工作流程**：执行流程说明
6. **输出示例**：预期输出

### Reference.md

Reference.md 提供技术参考资料：

1. **官方资源**：相关链接
2. **核心命令**：命令列表和说明
3. **配置文件路径**：配置文件位置
4. **环境变量**：可用的环境变量
5. **相关 Skill**：相关 Skill 链接

### 脚本文件

#### 文件头

```bash
#!/bin/bash

# ==========================================
# Script: skill-name.sh
# Description: 脚本描述
# Author: 作者名
# Version: 1.0.0
# ==========================================
```

#### 颜色定义

```bash
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color
```

#### 错误处理

```bash
# 严格模式
set -e

# 错误处理函数
error_exit() {
    echo -e "${RED}❌ 错误: $1${NC}" >&2
    exit 1
}

# 使用示例
command || error_exit "命令执行失败"
```

#### 日志记录

```bash
LOG_FILE=".gitnexus/skill-name.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 重定向输出
exec > >(tee -a "$LOG_FILE")
exec 2>&1
```

#### 进程管理

```bash
PID_FILE=".gitnexus/skill-name.pid"

# 保存进程 ID
save_pid() {
    echo $1 > "$PID_FILE"
}

# 清理旧进程
cleanup_old_process() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo -e "${YELLOW}🧹 清理旧进程 (PID: $OLD_PID)...${NC}"
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
}
```

## 命名规范

### Skill 名称

- 使用小写字母
- 使用短横线 `-` 连接单词
- 简洁明了，反映功能
- 示例：`gitnexus-setup`, `code-analyzer`, `doc-generator`

### 文件命名

- 脚本文件：`{skill-name}.sh`
- 文档文件：大写开头，`README.md`, `SKILL.md`, `Reference.md`
- 日志文件：`.gitnexus/{skill-name}.log`
- PID 文件：`.gitnexus/{skill-name}.pid`

## 输出规范

### 成功输出

```
==========================================
🎉 任务完成！
==========================================
📋 结果摘要:
   ✅ 步骤1完成
   ✅ 步骤2完成
💡 提示信息
==========================================
```

### 错误输出

```
❌ 错误: 具体错误信息

可能的原因:
1. 原因1
2. 原因2

解决方法:
命令或步骤
```

## 最佳实践

### 1. 幂等性

Skill 应该可以安全地多次执行：

```bash
# 检查是否已安装
if ! command -v tool &> /dev/null; then
    install_tool
fi
```

### 2. 异步执行

耗时操作应该在后台执行：

```bash
nohup long_running_task > logfile 2>&1 &
echo $! > "$PID_FILE"
```

### 3. 配置管理

支持多层级配置读取：

```bash
# 优先级: 环境变量 > 全局配置 > 默认值
CONFIG_VALUE="${ENV_VAR:-$(read_global_config 'key' 'default_value')}"
```

### 4. 用户提示

提供清晰的进度提示：

```bash
echo -e "${YELLOW}⏳ 正在执行操作...${NC}"
# 执行操作
echo -e "${GREEN}✅ 操作完成${NC}"
```

### 5. 安全检查

验证必要的前置条件：

```bash
# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        error_exit "需要 $1，请先安装"
    fi
}

check_command git
check_command node
```

## 示例 Skill

参考现有 Skill：

- [gitnexus-setup](../skills/gitnexus-setup/) - 环境初始化
- [gitnexus-wiki](../skills/gitnexus-wiki/) - Wiki 生成

## 提交检查清单

在提交新 Skill 前，请确认：

- [ ] 目录结构符合规范
- [ ] SKILL.md 包含完整的 YAML Front Matter
- [ ] README.md 清晰易懂
- [ ] 脚本文件可执行
- [ ] 脚本包含错误处理
- [ ] 已测试通过
- [ ] 更新了主 README.md 的 Skill 目录
