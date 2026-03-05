---
name: jira-integration
description: 零依赖的 Jira CLI 辅助技能 (基于 Python 3)，专为 Jira Server 7.5.2 优化，提供智能打单、查询、更新、流转和删除工单的集成能力。
---

# Jira CLI Integration Skill (AI Agent 指南)

当用户要求你操作 Jira 上的工单时，**你必须严格按照以下流程和契约调用本目录下的 Python CLI 脚本**。

## 关键契约与工作流 (The Contract)

这些脚本位于 `scripts_py/` 目录下，采用纯 Python 3 编写，适配 **Jira Server 7.5.2 (v2 API)**。

### 第一步：智能凭证获取策略 (Authentication & Setup)

当任何脚本返回 `"error_type": "MISSING_CREDENTIALS"` 或 `"error_type": "UNAUTHORIZED"` 时，AI 必须按照以下**三级递进策略**自动获取凭证：

**第一级：自动获取（IntegrationPlugin）**
1. 优先调用 `IntegrationPlugin.GetDefaultIntegrationAsync(4)` 获取 `ProjectManagement` 类型的默认集成凭证（Jira 配置）。
2. 如果返回 `success: true`，提取其 `endpoint`（即 Jira 域名）、`username` 和 `accessToken`，直接代入下方配置命令。
3. 如果返回 `success: false`（未配置集成），则**继续第二级**。

**第二级：本地缓存查找**
- 由于我们采用了工作空间隔离机制，这一级其实已经在 Python 脚本底层实现了。只要脚本在当前 `--workdir` 下找到过配置文件就会自动使用。如果底层依然报 `MISSING_CREDENTIALS`，说明当前目录无缓存，直接**进入第三级**。

**第三级：用户手动提供**
1. 停止后续操作，主动询问用户："我尝试了系统中已绑定的项目管理集成配置，但暂未找到对应的 Jira 凭证。请提供你的 **Jira 域名 (Host)**、**账号 (Username)** 和 **密码/API Token** 以便我连接系统。"
2. 收到信息后（无论来自第一级还是第三级），执行配置脚本：
   `python scripts_py/auth.py --domain "<Jira域名>" --user "<账号>" --token "<密码/Token>" --workdir "<用户工作空间tmp路径>"`
3. 配置成功后，重新执行用户原本请求的操作。
- **⚠️ 关键提示：凭证隔离**：必须始终传入 `--workdir` 以确保凭证存储在当前用户的隔离工作空间中（而非全局环境）。 

### 第二步：识别意图并调度工具 (Dispatcher)

> **⚠️ 必须传入工作空间**: 以下所有的脚本调用都**必须**在末尾附加 `--workdir "<用户工作空间tmp路径>"` ，否则将报错退出。

#### 意图 1：批量工单查询 (Search Issues)
- **脚本**：`python scripts_py/search.py --jql "<JQL>" --workdir "<用户工作空间tmp路径>"`
- **用法**：将自然语言转为 JQL。Jira 7.x 不支持 `accountId` 过滤，请使用 `assignee = 'username'` 或 `reporter = 'username'`。

#### 意图 1.5：查看单个工单详情 (Get Single Issue)
- **脚本**：`python scripts_py/get_issue.py --issue "<KEY>" --workdir "<用户工作空间tmp路径>"`
- **剧本**：用户说"看看这个单子"、"查一下 TEST-123"。它可以返回所有自定义字段的值，是决策前的重要参考。

#### 意图 2：智能打单 (Create Issue)
- **剧本**：用户要求创建一个 Bug、Feature 等。
- **两阶段机制**：
  1. **获取 Schema**：执行 `python scripts_py/schema.py --project "<KEY>" --issuetype "<Type>" --workdir "<用户工作空间tmp路径>"`。
  2. **校验与提交**：对比 Schema 中的 `required_fields`，缺项则反问。集齐信息后调用：
     `python scripts_py/create.py --payload '{"fields":{...}}' --workdir "<用户工作空间tmp路径>"`
- **💡 重要：Jira 7.x 人员字段请直接使用 `{"name": "username"}` 格式。**

#### 意图 3：工单内容更新 (Update Fields)
- **脚本**：`python scripts_py/update.py --issue "<KEY>" --payload '{"fields":{...}}' --workdir "<用户工作空间tmp路径>"`

#### 意图 3.5：工单状态流转 (Transition Workflow)
- **脚本**：
  1. 列出动作：`python scripts_py/transition.py --issue "<KEY>" --list --workdir "<用户工作空间tmp路径>"`
  2. 执行流转：`python scripts_py/transition.py --issue "<KEY>" --id "<TransitionID>" --workdir "<用户工作空间tmp路径>"`
- **剧本**：用户说"把单子关了"、"开始处理这个 Bug"。

#### 意图 4：工单删除 (Delete Issue)
- **脚本**：`python scripts_py/delete.py --issue "<KEY>" --workdir "<用户工作空间tmp路径>"`
- **风控**：在执行前，**必须**显式反问用户："你确定要永久删除工单 {KEY} 吗？此操作不可撤销。"。得到肯定答复（如"是的"、"确定"）后方可调用。

## 大模型避坑与自愈指南 (LLM Gotchas & Auto-Healing)

### 0. 记忆库分级读取策略
`MEMORY.md` 是你的渐进式大脑。**注意：`MEMORY.md` 是全局统一的资源知识库，不会受到 `--workdir` 的隔离影响。**
- **创建/更新前**：必读 §1 别名映射、§3 JSON 模板、§4 项目快照。
- **遇到 400 错后**：必读 §2 踩坑复盘，寻找 7.5.2 特有的字段报错解法。

### 1. 记忆库的自我进化
你被授权且**强制要求**在操作结束后更新 `MEMORY.md`：
- 发现新的自定义字段含义 -> 写入 §1。
- 攻克了一个变态校验字段 -> 写入 §3。
- 掌握了某个项目的工作流路径 -> 写入 §6。

### 2. 字段映射建议 (Jira 7.x 特色)
- **人员**：Jira 7.5.2 主要使用 `name`（登录名）进行映射。如果不知道 `name`，请先通过 `users_dict.py --keyword <姓名>` 查找。
- **日期**：通常格式为 `YYYY-MM-DD`。
- **级联/下拉**：优先参考 `schema.py` 返回的 `allowedValues` 信息。

### 3. 不要伪造
永远不要伪造 Transition ID 或字段名。如果不确定，先调用对应的查询/元数据脚本（`get_issue`, `schema`, `transition --list`）。
