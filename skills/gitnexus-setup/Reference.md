# GitNexus 官方参考资料

## 官方资源

- **GitHub**: https://github.com/abhigyanpatwari/GitNexus
- **Web UI**: https://gitnexus.vercel.app/

## 核心命令 (CLI Commands)

| 命令 | 说明 |
|------|------|
| `gitnexus analyze` | 解析当前 Git 仓库，生成 AST 与调用图谱（生成 `.gitnexus/`） |
| `gitnexus setup` | 为当前目录下的 AI 助手（如 Cursor, Claude Code）注入 MCP 配置 |
| `gitnexus serve --port <port>` | 在本地启动 HTTP 图谱微服务 |
| `gitnexus wiki --model <model> --base-url <url>` | 调用 LLM 生成架构 Wiki（依赖环境变量如 `OPENAI_API_KEY`） |

## 配置文件路径

| 配置类型 | 路径 |
|----------|------|
| 全局配置 | `~/.gitnexus/config.json` |
| 项目索引 | `.gitnexus/` |
| 分析日志 | `.gitnexus/analyze.log` |
| 服务日志 | `.gitnexus/serve.log` |
| 分析进程 ID | `.gitnexus/analyze.pid` |

## 环境变量

| 变量名 | 说明 |
|--------|------|
| `PORT` | Web UI 服务端口 |
| `OPENAI_API_KEY` | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 |

## 默认端口

- Web UI 服务：`54321`（避免与常用端口冲突）

## 相关 Skill

- [gitnexus-wiki](../gitnexus-wiki/) - 使用 GitNexus 生成项目架构 Wiki
