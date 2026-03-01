# GitNexus 环境初始化 Skill

## 简介

本 Skill 专为 Claude Code、OpenCode 等支持 MCP 的 AI 编程助手设计，用于全自动部署、管理和调度 [GitNexus](https://github.com/abhigyanpatwari/GitNexus)。

**重要提示**：所有输出和交互必须使用中文（简体中文）。

## 功能特性

- **自动全局安装**：检测并安装 npm 包 `gitnexus`
- **异步图谱构建**：后台运行 `gitnexus analyze` 生成 AST 索引
- **MCP 配置注入**：自动注册图谱检索工具到 AI 助手
- **自动同步钩子**：挂载 `post-commit` 钩子实现代码提交后自动更新（如已存在会先删除再创建）
- **守护进程管理**：进程防抖（防冲突）、全异步非阻塞执行
- **KùzuDB 防死锁**：启动前自动清理所有 gitnexus 相关进程

## 目录结构

```
gitnexus-setup/
├── SKILL.md              # Skill 主定义文件（AI 调用入口）
├── README.md             # 项目说明文档
├── Reference.md          # 官方命令与资源参考
└── scripts/
    └── gitnexus-setup.sh # 核心执行脚本
```

## 快速使用

对 AI 助手说：
> "初始化 GitNexus 环境"

或

> "配置 GitNexus"

## 工作流程

1. **环境验证**：检查 Git、npm 环境和 Git 仓库状态
2. **全局安装**：如未安装，自动执行 `npm install -g gitnexus`
3. **进程清理**：杀掉所有 gitnexus serve/analyze/wiki 进程，释放数据库锁
4. **代码分析**：后台异步运行 `gitnexus analyze`
5. **MCP 配置**：执行 `gitnexus setup` 注入配置
6. **钩子安装**：创建 `.git/hooks/post-commit` 自动同步脚本

## 常用命令

```bash
# 查看所有已索引的仓库列表
gitnexus list

# 查看当前仓库的索引状态
gitnexus status

# 启动本地 HTTP 服务器，连接 Web UI 查看图谱
gitnexus serve
# ⚠️ 注意: serve 命令会锁定数据库，运行期间无法执行 analyze/wiki
```

## 输出示例

```
🎉 GitNexus 环境已就绪！
==========================================
� 提示: 索引正在后台建立。运行 cat .gitnexus/analyze.log 查看进度。

� 常用命令:
   gitnexus list     - 查看所有已索引的仓库列表
   gitnexus status    - 查看当前仓库的索引状态
   gitnexus serve     - 启动本地 HTTP 服务器，连接 Web UI 查看图谱
   ⚠️ 注意: serve 命令会锁定数据库，运行期间无法执行 analyze/wiki
========================================
```

## 依赖要求

- Git
- Node.js 和 npm
- 当前目录必须是 Git 仓库

## 许可证

遵循 GitNexus 官方许可证
