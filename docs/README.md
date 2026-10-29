# Auto-Devnexus 文档中心

仓库文档按「入门 → 接入 → 规范 → 排障」四层组织。第一次来按顺序读，找具体问题时直接跳对应专题。

## 快速导航

| 文档 | 读者 | 内容 |
|------|------|------|
| [../README.md](../README.md) | 所有人 | 项目定位、22 个 Skill 能力一览、快速开始、凭据约定 |
| [getting-started.md](getting-started.md) | 首次使用 | 环境检查、安装、两种调用方式、常见故障排查 |
| [local-services.md](local-services.md) | 接入第三方服务的人 | 11 个本地服务 Skill 的申请入口、凭据配置、命令速查、能力边界 |
| [skill-specification.md](skill-specification.md) | Skill 作者 | 目录结构、`SKILL.md` 字段规范、脚本与输出约定、提交检查清单 |
| [windows-wezterm.md](windows-wezterm.md) | Windows 用户 | WezTerm 一键安装脚本的行为、生成文件与备份策略 |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献者 | 分支、提交、PR 流程与新增 Skill 的步骤 |

---

## 概念与架构

### 三层结构

1. **`SKILL.md`**：唯一权威说明。frontmatter 里的 `name` 与 `description` 决定 AI 助手何时加载它，正文描述执行步骤、边界和失败处理。
2. **`scripts/`**：真正干活的可执行脚本。AI 助手调用的是它，人工也能直接跑。
3. **`references/`、`README.md`、`Reference.md`**：按需加载的深水区材料，避免把长文档塞进 `SKILL.md`。

### 两种 Skill 形态

| 形态 | 特征 | 例子 |
|------|------|------|
| 执行型 | 带 `scripts/`，AI 助手拼参数直接调用 | `amap`、`cloudflare`、`web-search` |
| 指导型 | 无脚本，靠 `SKILL.md` + `references/` 约束方法论 | `open-source-docs`、`frontend-ui-ux`、`codebase-memory-mcp-setup` |

### 接入型 Skill 的通用设计

官方只提供 MCP、只提供 CLI、或只提供 REST 的服务，统一做一层薄封装：

- 不向用户的 `.mcp.json` 注入配置，避免污染编辑器全局状态
- 脚本零第三方依赖，只用 Python 标准库
- 凭据走环境变量或用户目录，仓库内只有 `.env.example`
- 只读优先：查询类接口默认开放，涉及下单与支付的接口必须显式确认

---

## 接入与使用

- 第一次接入某个服务，先读 [local-services.md](local-services.md) 里对应章节，拿到「申请入口 → 凭据落位 → 首条验证命令」再动手。
- 具体参数与子命令，以该 Skill 目录下的 `SKILL.md` 为准。
- 新增或修改 Skill 后，同步更新本文件与根 `README.md` 的能力一览。

---

## 开发与运维

- Skill 编写规范：[skill-specification.md](skill-specification.md)
- 贡献流程：[../CONTRIBUTING.md](../CONTRIBUTING.md)
- CI：`.github/workflows/ci.yml`

---

## 排障速查

| 现象 | 先查 |
|------|------|
| 脚本报权限错误 | [getting-started.md](getting-started.md) 的「故障排除」 |
| 第三方服务 401 / 403 / Key 无效 | [local-services.md](local-services.md) 对应章节的「凭据配置」 |
| 端口 54321 被占用、图谱为空 | [getting-started.md](getting-started.md) 的 GitNexus 排障 |
| AI 助手不触发某个 Skill | 该 Skill 的 `SKILL.md` frontmatter `description` 是否覆盖了你的说法 |
