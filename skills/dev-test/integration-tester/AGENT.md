---
name: integration-tester
description: 对任意项目执行或设计集成测试，覆盖 API、Service、数据库、消息队列、外部依赖、CLI 与服务端协作等模块间行为。适用于“集成测试、接口联调测试、服务协作验证、模块集成验证”等请求。必须复用 test-governance-core。
---

# Integration Tester

用于验证模块协作，不处理纯视觉问题。

## 流程

1. 使用 `test-governance-core` 识别技术栈、测试框架、集成边界和跨服务/多项目范围。
2. 若用户提供用例，先映射到相关源码、接口/CLI、配置、数据模型、文档依据和已有测试。
3. 先确认真实环境、真实服务、真实账号、租户、真实测试数据边界和外部依赖可达性；缺少任一必要信息时，**暂停当前流程并主动向用户追问缺失项，等用户补齐后立即继续执行**，不得只输出清单后退出。
4. **如本轮包含浏览器操作（导航/点击/表单/读页面/截图等）**，先执行 `bsk doctor`；若未安装、daemon 未就绪或扩展未连接，按 `references/ui-tooling.md` 的"BrowserSkill 缺失时的引导流程"协助用户完成 CLI、agent skill 和浏览器扩展安装/连接，**安装动作必须先获得用户明确确认**；用户拒绝时按降级方案处理。
5. 定位已有 integration / e2e / api / service 测试，以及各相关项目的测试入口。
6. 只有真实环境可测且数据边界明确时，才优先运行项目原生集成测试命令。
7. 如需新增测试，先做影响面分析，再按项目现有测试风格补最小用例。
8. 覆盖成功路径和关键失败路径，尤其是鉴权、权限、租户、数据一致性、跨服务契约和外部依赖错误。
9. 输出命令、断言、依赖状态、跨服务未验证项和风险；缺少真实环境数据时不输出执行命令或通过结论，**主动向用户追问缺失项并等待补齐后再继续**，不得只输出阻断原因后退出。
10. 默认只运行受影响范围，并在 `test-governance/reports/` 追加本次集成测试报告；除非用户明确要求全量。

## 工具选择

- Node/Nest/Express：Jest、Vitest、Supertest。
- Python：pytest、requests/httpx test client。
- Java/Kotlin：JUnit、Spring test。
- Go：go test、httptest。
- Rust：cargo test、集成测试目录。
- .NET：xUnit/NUnit/MSTest、WebApplicationFactory。
