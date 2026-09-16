---
name: bug-ui-delta-tester
description: 基于 bug 影响面选择最小增量 UI 测试集，覆盖受影响页面、组件、表单、交互、导航、截图证据和用户路径。适用于“基于 BUG 做增量 UI 测试、修复后页面验证、UI bug 回归”等请求。必须复用 test-governance-core 的 UI 工具策略。
---

# Bug UI Delta Tester

用于 UI bug 修复后的最小界面验证。

## 流程

1. 使用 `test-governance-core` 收集 bug、代码和文档上下文。
2. 先确认真实 URL、真实账号、真实租户、真实测试数据和数据边界；缺少任一必要信息时，**暂停当前流程并主动向用户追问缺失项，等用户补齐后立即继续执行**，不得只输出清单后退出。
3. 读取 `references/bug-delta-rules.md` 与 `references/ui-tooling.md`。
4. **BrowserSkill 健康检查**：执行 `bsk doctor`。若未安装、daemon 未就绪或扩展未连接，按 `references/ui-tooling.md` 中"BrowserSkill 缺失时的引导流程"协助用户完成 CLI、agent skill 和浏览器扩展安装/连接，**安装动作必须先获得用户明确确认**；用户拒绝时按降级方案处理。
5. 将 bug 或用户用例映射到受影响页面、路由、组件、表单、样式、交互、源码和文档依据。
6. 若 UI 行为依赖跨服务接口、网关、鉴权、租户或数据流，列出相关服务和未验证依赖，再裁剪最小 UI 验证路径。
7. 轻量验证优先真实浏览器桥和截图证据。
8. 长期反复回归的 UI bug 再补项目已有 Playwright/Cypress/Selenium 用例；若缺少工具，按 core 规则指导安装 BrowserSkill，不自动安装 Playwright。
9. 输出 URL、步骤、断言、截图/报告和未覆盖风险。
10. 默认只追加本次 bug 增量 UI 报告，截图证据放入 `test-governance/evidence/screenshots/`。

## 升级为长期 UI 回归的条件

- 同类 UI bug 重复出现。
- 涉及 P0 用户路径。
- 需要 CI gate 防止再次发布。
- 只靠人工或浏览器桥难以稳定复验。
