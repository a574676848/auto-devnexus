---
name: repo-parser
description: 仓库解析技能，用于自动解析并读取 GitHub 和各类私有 Git 仓库源码，包含智能凭证管理和分块深度阅读策略。注意：脚本在技能目录下，执行在当前项目目录下。
---
# 仓库解析技能 (Repo-Parser)

本技能用于解析并读取 GitHub（公开/私有）和各类私有 Git（GitLab, Gitea, 局域网仓库等）仓库源码。系统应根据 URL 类型自动选择解析脚本，并统一按**两步走**策略进行深度阅读，避免产生代码幻觉或由于上下文超载导致崩溃。

---

## 🔑 智能凭证获取策略 (极其重要 — 必须严格按顺序执行)

当需要访问**任何私有仓库**或**GitHub 私有仓库**时，AI 必须按照以下**三级递进策略**自动获取凭证，而非直接询问用户：

### 第一级：自动获取（IntegrationPlugin）
1. **优先调用** `IntegrationPlugin.GetDefaultIntegrationAsync(2)` 获取 `CodeRepository` 类型的默认集成凭证。
2. 如果返回 `success: true`，直接使用返回的 `credential` 字段作为 Git Token。
3. 如果返回 `success: false`（未配置集成），则**继续第二级**。

### 第二级：本地缓存查找
1. 尝试读取 `%USERPROFILE%\.repo-parser\credential_cache.json` 文件。
2. 按仓库域名（如 `gitlab.example.com`、`gitea.mycompany.cn`）进行精确匹配。
3. 如果命中缓存凭证，使用该 Token 尝试操作。
4. 如果缓存文件不存在或无匹配域名，则**继续第三级**。

#### 缓存文件格式（`%USERPROFILE%\.repo-parser\credential_cache.json`）
```json
{
  "credentials": [
    {
      "domain": "gitlab.example.com",
      "token": "glpat-xxxxxxxxxxxx",
      "note": "用户于2026-03-04提供",
      "updated_at": "2026-03-04T12:00:00+08:00"
    }
  ]
}
```

### 第三级：用户手动提供
1. 以**极其友好的中文**向用户解释当前情况并索要 Token。
   *示例："我尝试了系统中已绑定的集成配置，但暂未找到适用于 `gitlab.example.com` 的 Git 凭证。您可以提供一个该平台的 Personal Access Token (PAT) 吗？我会安全地缓存在本地，后续使用同一仓库时就不需要再提供了。"*
2. 获取到 Token 后，**立即写入** `%USERPROFILE%\.repo-parser\credential_cache.json` 进行缓存持久化（追加或更新对应域名记录）。
3. 然后使用 Token 继续执行解析。

### 凭证失败重试逻辑
- 当脚本返回 `auth_required`（无凭证可用）: 直接进入第三级，向用户索要。
- 当脚本返回 `auth_invalid`（凭证已过期或无权限）: 告知用户当前凭证已失效，要求提供新的 Token，并**更新**缓存。
  *示例："当前使用的 Git 凭证似乎已经过期或没有访问该仓库的权限。能否提供一个新的有效令牌？"*

---

## 核心解析脚本与配置

> ⚠️ **关键提示**：脚本文件（A 目录）和执行工作目录（B 目录）是分离的。
> 仓库代码**必须克隆到 B 目录**（用户的工作空间 tmp 路径），而非脚本所在的 A 目录。
> 所有脚本通过 `--workdir` 参数指定输出目录，脚本会在该目录下创建 `temp_repo/` 子目录进行 `git clone/pull`。
>
> **调用方式**：`${SKILL_DIR}/scripts/parse_xxx.py <url> --workdir "$(pwd)/temp_repo_target"`

### 1. GitHub 仓库
当用户提供 `github.com` 链接时：
- **公开仓库**：直接调用，无需传入 Token：
  ```
  ${SKILL_DIR}/scripts/parse_github.py <url> --workdir <用户工作空间tmp路径>
  ```
- **私有仓库**：走上述**三级凭证策略**获取 Token 后，通过环境变量 `GITHUB_TOKEN` 注入：
  ```
  GITHUB_TOKEN=<token> ${SKILL_DIR}/scripts/parse_github.py <url> --workdir <用户工作空间tmp路径>
  ```
- **如何判断公开/私有**：先不传 Token 直接执行，如果脚本返回 `auth_required`，则判定为私有仓库，启动凭证策略。

### 2. 本地/私有仓库 (GitLab, Gitea, 内网等)
当用户提供非 GitHub 的仓库链接时：
- **始终走凭证策略** — 因为非 GitHub 仓库大概率需要鉴权。
- **执行命令**：获取 Token 后，通过环境变量 `GIT_TOKEN` 注入：
  ```
  GIT_TOKEN=<token> ${SKILL_DIR}/scripts/parse_local_git.py <url> --workdir <用户工作空间tmp路径>
  ```
- **机制**：底层在指定的 `--workdir` 目录下创建 `temp_repo/` 子目录进行 `git clone/pull`，并主动过滤不相关的编译产物与多媒体文件。

---

## 🛠️ 标准化 AI 交互契约 (极其重要)

无论是 GitHub 还是私有 Git，Python 脚本执行成功后**必将严格输出以下格式的 JSON**:
```json
{
  "status": "success",
  "tree_file": "workdir/REPO_TREE_OUTPUT.md",
  "output_files": ["workdir/REPO_CONTENT_PART_1.md", "..."],
  "message": "解析成功提示语"
}
```

错误时返回：
```json
{
  "status": "error",
  "reason": "auth_required | auth_invalid | too_large | git_error | env_missing | invalid_url",
  "message": "人类可读的错误描述"
}
```

**⚠️ AI 必须严格遵守以下执行流进行回答（严禁自作主张或忽略步骤）⚠️**

### 第一步：宏观感知 (只读大纲)
1. 获取 JSON 后，**强制读取 `tree_file` 路径的文件**（包含目录结构与骨架）。
2. **分析与友好回复**：使用**非常友好的中文**，概括性地告诉用户解析的大概情况。
   *示例范本："我已经成功拉取并梳理了该仓库的结构。这是一个采用了 X 架构的工程，核心代码似乎在 Y 目录下。为了更精准地回答您的问题，请问您想先深入查看某个具体模块的源码吗？还是针对该项目某个整体特性有疑问？"*

### 第二步：微观查取 (按需读详文)
根据用户给出的重点或追问，内部悄悄通过工具读取对应切片的 `output_files` 源文件获取上下文，再给出专业、深入的技术回答。

---

## 异常熔断与友好拒绝
当 JSON 返回了如由于代码过于庞大防爆内存而生成的 `"status": "error", "reason": "too_large"` 时，不能继续强行阅读，而是使用极具包容和**友好的中文**向用户解释：
*"抱歉，这个仓库的代码量实在太庞大了，我一口气吃不下这么多内容。关于超大工程的 RAG 向量搜索功能我们正在开发中，您可以针对局部文件提问哦！"*

## 强制底线约束
- 严禁对任何 Git 仓库链接单独使用 `<search_web>` 工具瞎搜，那只是浅层 HTML。
- 所返回的所有状态、回复以及向终端用户展示的信息**必须是简体中文**，且语气诚挚友好。
- **凭证安全**：绝不在回复中明文显示用户的 Token，如需引用仅用 `***` 脱敏。
- **凭证缓存**：只持久化到 `%USERPROFILE%\.repo-parser\credential_cache.json`，不在对话记录中留存原始 Token。

## 技能文件位置说明

本 Skill 可能位于以下目录之一：
- `~/.claude/skills/` - Claude Code 技能目录
- `~/.config/opencode/skills/` - OpenCode 技能目录
- `~/.cc-switch/skills/` - CC-Switch 技能目录

### ⚠️ 技能目录 vs 执行目录（重要）

**技能目录（A）**：SKILL.md 和脚本所在的目录。
**执行目录（B）**：当前用户工作目录（即当前项目根目录）。

**脚本位于 A 目录，但需要在 B 目录执行。** 仓库 clone 和输出文件必须写入 B 目录（或其子目录），而非 A 目录。

执行时必须使用 A 目录的脚本路径，并通过 `--workdir` 参数告诉脚本目标目录：

```bash
# 1. 先确定技能目录的绝对路径（根据实际安装位置调整）
SKILL_DIR="你的技能目录绝对路径"  # 例如 ~/.claude/skills/repo-parser

# 2. 在执行目录（B，即当前项目根目录）下运行脚本，传入 --workdir
"${SKILL_DIR}/scripts/parse_github.py" <url> --workdir "$(pwd)/temp_target"
```

如果脚本返回凭证相关的错误，按**三级递进策略**获取 Token 后重新执行。
