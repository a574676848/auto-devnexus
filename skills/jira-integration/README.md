# Jira 集成技能 (jira-integration)

## 📋 技能介绍

Jira 集成技能是一个零依赖的 Jira CLI 辅助工具，专为 Jira Server 7.5.2 优化，提供智能打单、查询、更新、流转和删除工单的集成能力。

### ✨ 功能特性

- **零依赖**：纯 Python 3 实现，无需额外安装依赖
- **Jira Server 7.5.2 优化**：专门适配 v2 API
- **完整工单操作**：支持查询、创建、更新、流转和删除工单
- **智能打单**：两阶段机制，先获取 schema 再提交
- **项目复盘报告生成**：支持基于 Jira 全量数据和参考资料生成 PPT 风格复盘 Markdown
- **多层认知记忆**：内置 MEMORY.md 系统，持续学习和进化
- **安全认证**：支持密码和 API Token 认证

## 🚀 快速开始

### 前置要求

- Python >= 3.6
- Jira Server 7.5.2（或兼容版本）

### 初始化配置

首次使用时，需要配置 Jira 连接信息：

```bash
# 配置 Jira 连接信息
python scripts_py/auth.py --domain "https://your-jira-domain.com" --user "your-username" --token "your-password-or-api-token"
```

### 基本使用

#### 查询工单

```bash
# 使用 JQL 查询工单
python scripts_py/search.py --jql "assignee = currentUser() AND status = 'Open'"

# 获取单个工单详情
python scripts_py/get_issue.py --issue "TEST-123"
```

#### 创建工单

```bash
# 先获取项目和工单类型的 schema
python scripts_py/schema.py --project "TEST" --issuetype "Bug"

# 然后创建工单
python scripts_py/create.py --payload '{"fields":{"project":{"key":"TEST"},"summary":"测试工单","description":"这是一个测试工单","issuetype":{"name":"Bug"},"assignee":{"name":"your-username"}}}'
```

#### 更新工单

```bash
# 更新工单字段
python scripts_py/update.py --issue "TEST-123" --payload '{"fields":{"summary":"更新后的工单标题","description":"更新后的工单描述"}}'
```

#### 工单状态流转

```bash
# 列出可用的状态流转
python scripts_py/transition.py --issue "TEST-123" --list

# 执行状态流转
python scripts_py/transition.py --issue "TEST-123" --id "21"
```

#### 删除工单

```bash
# 删除工单（谨慎操作，不可撤销）
python scripts_py/delete.py --issue "TEST-123"
```

#### 生成项目复盘报告

```bash
# 1. 导出 Jira 全量复盘数据
python scripts_py/review_export.py --issue "EXEPD-205110" --workdir "<用户工作空间 tmp 路径>"

# 2. 收集参考资料（可选，本地文件 / URL / Jira 描述链接）
python scripts_py/review_refs.py --issue "EXEPD-205110" --workdir "<用户工作空间 tmp 路径>" --file "D:\docs\需求文档.md"

# 3. 分析并生成复盘报告
python scripts_py/review_analyze.py --issue "EXEPD-205110" --workdir "<用户工作空间 tmp 路径>" --role "姓名=角色"
python scripts_py/review_render.py --issue "EXEPD-205110" --workdir "<用户工作空间 tmp 路径>"

# 4. 或直接一键生成
python scripts_py/review_generate.py --issue "EXEPD-205110" --workdir "<用户工作空间 tmp 路径>" --file "D:\docs\需求文档.md"
```

## 🧠 记忆系统

本技能内置了多层认知记忆系统 (`MEMORY.md`)，用于：

- **别名映射**：记录用户口语与系统字段的对应关系
- **踩坑复盘**：记录 API 调用失败的原因和解决方案
- **JSON 模板**：存储复杂字段的正确结构
- **项目快照**：缓存项目元数据，加速操作
- **JQL 模式**：积累常用的 JQL 查询模式
- **工作流地图**：记录状态流转的合法路径
- **用户画像**：学习用户的操作偏好
- **决策日志**：记录重要的决策过程

## 🔧 脚本说明

| 脚本名称 | 功能 | 用法 |
|---------|------|------|
| `auth.py` | 身份认证和配置 | `--domain <域名> --user <用户名> --token <密码/Token>` |
| `search.py` | 查询工单 | `--jql <JQL 查询语句>` |
| `get_issue.py` | 获取工单详情 | `--issue <工单KEY>` |
| `schema.py` | 获取工单 schema | `--project <项目KEY> --issuetype <工单类型>` |
| `create.py` | 创建工单 | `--payload <JSON  payload>` |
| `update.py` | 更新工单 | `--issue <工单KEY> --payload <JSON  payload>` |
| `transition.py` | 工单状态流转 | `--issue <工单KEY> --list` 或 `--id <流转ID>` |
| `delete.py` | 删除工单 | `--issue <工单KEY>` |
| `review_export.py` | 导出复盘数据包 | `--issue <工单KEY> --workdir <路径>` |
| `review_refs.py` | 收集参考资料 | `--issue <工单KEY> [--file <路径>] [--url <URL>] --workdir <路径>` |
| `review_analyze.py` | 分析复盘数据 | `--issue <工单KEY> [--role <姓名=角色>] --workdir <路径>` |
| `review_render.py` | 渲染复盘报告 | `--issue <工单KEY> --workdir <路径>` |
| `review_generate.py` | 一键生成复盘报告 | `--issue <工单KEY> [--file <路径>] [--url <URL>] [--role <姓名=角色>] --workdir <路径>` |
| `utils.py` | 工具函数 | 内部使用 |

## 📝 注意事项

1. **Jira 7.5.2 特性**：该技能专为 Jira Server 7.5.2 优化，使用 `name` 字段进行用户映射，不支持 `accountId`。

2. **安全提醒**：认证信息会存储在本地配置文件中，请确保文件权限安全。

3. **操作风险**：删除工单操作不可撤销，请谨慎使用。

4. **API 限制**：请遵守 Jira 服务器的 API 调用频率限制。

5. **记忆系统**：每次操作后，AI 助手会自动更新 `MEMORY.md` 文件，记录经验和解决方案。
6. **UTF-8 规范**：所有复盘脚本和输出文档统一采用 UTF-8 编码。
7. **参考资料优先级**：本地文件 > 用户 URL > Jira 描述中的链接；若环境为 openclaw，可由大模型主动识别并优先用 browser 模拟读取正文。

## 🔍 故障排除

### 常见问题

1. **认证失败**：检查 Jira 域名、用户名和密码是否正确。

2. **400 错误**：通常是 JSON payload 格式错误，请参考 `MEMORY.md` 中的模板。

3. **权限不足**：检查用户是否有相应的操作权限。

4. **状态流转失败**：使用 `transition.py --list` 查看可用的流转路径。

### 日志查看

执行脚本时，可添加 `--verbose` 参数查看详细日志：

```bash
python scripts_py/search.py --jql "assignee = currentUser()" --verbose
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进此技能！

## 📄 许可证

本项目采用 MIT 许可证开源。
