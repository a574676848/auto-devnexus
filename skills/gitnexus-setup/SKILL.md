---
name: "gitnexus-setup"
description: "自动化安装、配置 GitNexus，注入 MCP 配置、挂载 post-commit 钩子、启动守护进程。当用户要求初始化、配置或重置 GitNexus 环境时调用。"
---

# GitNexus 环境初始化 Skill

## 技能描述

此 Skill 用于在当前 Git 仓库中全自动化安装、配置和管理 GitNexus 的后台守护进程。具备幂等性（Idempotent）和进程防抖能力，确保 AI 上下文库和本地 Web UI 始终与最新代码保持同步。

## 触发条件

当用户说出以下关键词时调用此 Skill：
- "初始化 GitNexus"
- "配置 GitNexus"
- "设置 GitNexus"
- "启动 GitNexus"
- "重置 GitNexus 环境"
- "安装 GitNexus"

## 执行步骤（必须按顺序执行）

### 步骤 1：执行安装脚本
**必须立即执行以下命令**：
```bash
./scripts/gitnexus-setup.sh
```

### 步骤 2：处理权限错误（如需要）
如果步骤 1 返回 "Permission denied" 错误，**必须先执行赋权命令**：
```bash
chmod +x ./scripts/gitnexus-setup.sh
```
然后**重新执行步骤 1**。

### 步骤 3：验证执行结果
- 如果脚本返回成功（exit code 0）：向用户展示"预期输出"中的信息
- 如果脚本返回错误：根据错误信息提示用户

## 核心能力

1. **全局安装**：检测并安装 npm 包 `gitnexus`
2. **异步图谱构建**：运行 `gitnexus analyze` 生成 AST 索引
3. **MCP 注入**：运行 `gitnexus setup` 注册图谱检索工具
4. **自动同步钩子**：创建并赋权 `.git/hooks/post-commit` 实现静默更新
5. **守护进程管理**：杀掉旧的 `gitnexus serve` 进程，重新在端口 54321 启动服务

## 预期输出

执行成功后，向用户展示：
- Web UI 本地访问地址：`http://localhost:54321`
- Web UI 云端访问地址：`https://gitnexus.vercel.app/?server=http://localhost:54321`
- 查看索引进度命令：`cat .gitnexus/analyze.log`

## 质量评估标准

1. **幂等性**：多次执行结果一致，不产生错误
2. **进程防抖**：启动新进程前终止旧进程
3. **后台执行**：分析任务异步运行，不阻塞用户
4. **钩子持久化**：post-commit 钩子能 survive 仓库操作
5. **服务可用性**：Web UI 在配置端口可访问
6. **错误处理**：对缺失前置条件给出清晰提示

## 参考资料

详见 [Reference.md](./Reference.md)
