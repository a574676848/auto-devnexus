# GitNexus Wiki 参考资料

## 官方资源

- **GitHub**: https://github.com/abhigyanpatwari/GitNexus
- **Web UI**: https://gitnexus.vercel.app/

## 核心命令 (CLI Commands)

| 命令 | 说明 |
|------|------|
| `gitnexus analyze` | 解析当前 Git 仓库，生成 AST 与调用图谱 |
| `gitnexus setup` | 为当前目录下的 AI 助手注入 MCP 配置 |
| `gitnexus serve --port <port>` | 在本地启动 HTTP 图谱微服务 |
| `gitnexus wiki --model <model> --base-url <url>` | 调用 LLM 生成架构 Wiki |

## Wiki 命令参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--api-key` | 指定 API 密钥 | `--api-key sk-xxx` |
| `--model` | 指定模型名称 | `--model gpt-4` |
| `--base-url` | 自定义 API 端点 | `--base-url https://api.openai.com/v1` |

## 环境变量

| 变量名 | 说明 |
|--------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 |
| `API_KEY` | 通用 API 密钥（脚本使用） |
| `BASE_URL` | 自定义 API 基础 URL |
| `MODEL` | 模型名称 |

## 配置文件路径

### GitNexus 全局配置
- **路径**: `~/.gitnexus/config.json`
- **用途**: 存储 LLM API 配置，供后续使用

### OpenCode 配置
- **路径**: `~/.config/opencode/opencode.json`

### Claude Code 配置
- **路径**: `~/.claude/settings.json`

## 配置文件字段映射

| 标准字段 | GitNexus | OpenCode | Claude |
|----------|----------|----------|--------|
| API Key | `apiKey` | `provider.{key}.options.apiKey` | `env.ANTHROPIC_AUTH_TOKEN` |
| Base URL | `baseUrl` | `provider.{key}.options.baseURL` | `env.ANTHROPIC_BASE_URL` |
| Model | `model` | `provider.{key}.models.{firstKey}` | `env.ANTHROPIC_MODEL` |

**说明**：
- OpenCode 配置使用第一个 provider（如 `openai`、`anthropic` 等）
- 模型名称使用 provider.models 中的第一个 key

## 日志文件

| 文件路径 | 说明 |
|----------|------|
| `.gitnexus/wiki.log` | Wiki 生成日志 |
| `.gitnexus/wiki.pid` | Wiki 进程 ID 文件 |

## 进程管理

| 操作 | 命令 |
|------|------|
| 查看日志 | `tail -f .gitnexus/wiki.log` |
| 停止进程 | `kill -9 $(cat .gitnexus/wiki.pid)` |

## 相关 Skill

- [gitnexus-setup](../gitnexus-setup/) - 初始化 GitNexus 环境
