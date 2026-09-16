---
name: ui-tester
description: 对任意 Web、桌面或移动项目的产品原型/UI设计稿与实际UI进行视觉比对。适用于”UI视觉验证、设计稿比对、像素级对比、视觉回归”等请求。浏览器功能操作（导航、点击、填写、表单提交、列表CRUD）归入集成测试，应使用 test-governance-core 的集成测试流程。必须复用 test-governance-core 的 UI 工具选择策略。
---

# UI Tester

用于验证产品原型或 UI 设计稿与实际渲染 UI 的视觉一致性。

## 视觉比对流程

1. 使用 `test-governance-core` 识别项目 UI 类型和已有视觉比对工具。
2. 获取设计稿来源：Figma 链接/设计稿文件路径/版本号。
3. 确认真实页面 URL、账号和访问权限；缺少时**暂停当前流程并主动向用户追问缺失项，等用户补齐后立即继续执行**，不得只输出清单后退出。
4. **BrowserSkill 健康检查**：执行 `bsk doctor`。若未安装、daemon 未就绪或扩展未连接，按 `references/ui-tooling.md` 中"BrowserSkill 缺失时的引导流程"协助用户完成 CLI、agent skill 和浏览器扩展安装/连接，**安装动作必须先获得用户明确确认**；用户拒绝安装时按降级方案（复用项目已有 Playwright/Cypress 或只输出手工步骤）继续。
5. 使用截图工具或视觉比对框架（Percy/Chromatic/Playwright Visual Comparison）获取实际 UI 渲染截图。
6. 执行比对：布局、色彩、字体、图标、圆角、间距、响应式断点、组件状态（hover/focus/active/disabled/error）。
7. 记录差异清单：位置偏移、尺寸差异、色差、缺失/多余元素。
8. 输出视觉比对报告，包含设计稿来源、比对范围、比对工具、差异清单和截图证据。
9. 默认在 `test-governance/reports/` 追加本次视觉比对报告，截图放入 `test-governance/evidence/screenshots/`。

## 操作方式

- 视觉比对是 UI Tester 的核心职责。
- 浏览器功能操作（导航、点击、填写、表单提交、列表 CRUD）不属于 UI 测试，应使用 `test-governance-core` 按集成测试流程执行。
- 所有浏览器功能操作必须使用模拟真实操作：调用真实服务地址、真实 API、真实浏览器。

## 不做的事

- 不用 UI 视觉测试替代后端权限、数据一致性或业务边界测试。
- 不为一次性轻量验收强行引入重型 UI 框架。
- UI 视觉测试不验证业务流程正确性——浏览器功能操作归入集成测试。
- 不对缺少设计稿的项目做无参照的 UI 视觉测试。
