# UI Tooling

## 定位

UI 测试的边界是**视觉比对**：验证产品原型或 UI 设计稿与实际渲染 UI 的一致性。浏览器功能操作（导航、点击、填写、表单提交、列表 CRUD）归入集成测试，通过 API + 真实浏览器工具完成。

## 选择顺序

| 目标 | 首选 | 说明 |
| --- | --- | --- |
| 视觉比对 | Figma API + Percy/Chromatic/Playwright Visual Comparison，或 BrowserSkill 截图 + 设计稿叠加 | 像素级或结构级比对，验证设计与实现的一致性 |
| 集成测试浏览器操作 | 本机已安装的 BrowserSkill 或现有浏览器桥 | 导航、点击、填写、读取页面、截图、真实登录态验收，属于集成测试范畴 |
| CI 级 UI 回归 | 项目已有 Playwright / Cypress / Selenium | 可重复、可断言、可报告 |
| 失败排障 | Chrome DevTools / network / console | 用于定位，不作为测试框架 |
| 无 UI 自动化框架 | 指导用户安装 BrowserSkill，或生成手工步骤 | 未经用户明确要求，不自动安装 Playwright |

## 工具可用性判定

1. 本机有 BrowserSkill 且 `bsk doctor` 无失败项时，集成测试的浏览器操作和视觉比对截图优先使用 BrowserSkill。
2. 本机没有 BrowserSkill，但项目已经安装并配置 Playwright / Cypress / Selenium 时，可以复用项目已有命令执行最小必要用例。
3. 本机没有 BrowserSkill，且项目没有可用的 Playwright / Cypress / Selenium 时，禁止自动安装 Playwright；按下方"BrowserSkill 缺失时的引导流程"协助用户安装 CLI、skill 和浏览器扩展。
4. 只有用户明确要求安装 Playwright，或项目文档/任务明确以 Playwright 作为交付目标时，才允许提供或执行 Playwright 安装步骤。

## BrowserSkill 健康检查（每次浏览器操作前必做）

进入需要浏览器的流程（视觉比对 / 集成测试浏览器操作 / Bug-UI 增量验证）前，先执行：

```powershell
bsk doctor
```

按返回结果路由：

| 观察到 | 处理方式 |
|---|---|
| `bsk doctor` 无 `fail` 且扩展已连接 | 健康，直接进入测试流程 |
| `command not found` 或 `bsk` 不可用 | 进入"未安装"引导（见下） |
| `bsk doctor` 报告 daemon 未运行 | 按 doctor 输出的提示启动或重试 `bsk doctor` |
| `bsk doctor` 报告扩展未连接 | 进入"扩展未连接"引导 |

## BrowserSkill 缺失时的引导流程

**关键原则**：dev-test 不在本地重复实现 BrowserSkill 安装逻辑；统一依据官方安装指南 `https://github.com/Tencent/BrowserSkill/blob/main/AGENT_INSTALL.md` 执行，并由用户完成浏览器扩展安装。

具体流程：

### 情况一：CLI 未安装

1. 主动告知用户"未检测到 BrowserSkill，需要安装 CLI、agent skill 和浏览器扩展后才能进行真实浏览器操作和视觉比对"。
2. 询问用户是否同意安装。**安装属于中等风险动作，必须等用户明确确认后才执行**。
3. 用户同意后，在 Windows PowerShell 执行官方安装命令：
   ```powershell
   irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex
   bsk --version
   ```
   其他系统按官方指南使用 `install.sh`。
4. 按当前 agent harness 执行 `bsk install-skill`（或 `bsk install-skill --harness <harness> --json`），再执行 `bsk doctor`。
5. 如果用户拒绝安装：暂停浏览器相关测试流程；对当前任务给出降级方案（项目已有 Playwright/Cypress 时复用，否则只生成手工步骤清单），并明确告知"未安装 BrowserSkill 的限制范围"。

### 情况二：已安装但 daemon 未就绪

1. 执行 `bsk doctor` 并遵循输出的 `hint`，不要猜测进程路径或手工删除运行文件。
2. 按 doctor 提示启动 daemon，重新运行 `bsk doctor` 验证。
3. 若仍失败，转交官方 `AGENT_INSTALL.md` 和 README 的故障排查说明。

### 情况三：daemon 已就绪但浏览器扩展未连接

1. 告知用户：
   > "BrowserSkill CLI/daemon 已就绪，但浏览器扩展未连接。请按浏览器类型安装扩展：Chrome 使用 [Chrome Web Store](https://chromewebstore.google.com/detail/hhcmgoofomhgciiibhipgmgkgnoenaoi)，Microsoft Edge 使用 [Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/browserskill/emacgiaaaiojkkpkddmmdfhmokgmnikg)。安装后打开扩展弹窗，等待状态变绿。"
2. 等用户确认操作后再次执行 `bsk doctor` 验证；扩展连接前不进入浏览器测试流程。

### 情况四：进入更深层故障排查

任何"CLI/daemon 已安装但仍跑不起来"的问题（daemon 启动失败、扩展反复掉线、tool 调用超时、多浏览器冲突等），不要在 dev-test 这边自行猜测；提示用户参考官方 `AGENT_INSTALL.md`、README 和 `bsk doctor` 输出处理。

## BrowserSkill 边界

适合：导航、点击、填写、读取页面、截图、真实登录态验收（属于集成测试的浏览器操作手段，非 UI 视觉测试工具）。

不适合：大规模 CI、复杂断言矩阵、多浏览器覆盖、稳定 trace/report、像素级视觉比对。

## 页面元素勘测与流程固化

集成测试的浏览器操作前必须完成页面元素勘测，减少自动化操作中的猜测：

1. 先从源码或路由文件确认目标页面路径、表单字段、按钮文案、弹窗标题、列表列名、状态文案和接口调用。
2. 再用真实浏览器快照确认线上页面实际呈现的字段、按钮、链接、弹窗和关键文本，记录可访问性名称或稳定选择器。
3. 若源码与真实页面不一致，以真实页面为当前执行依据，并在报告中记录差异和风险。
4. 将确认后的操作流程固化到被测项目 `test-governance/reports/` 或 `test-governance/test-cases.md`：包括页面 URL、元素清单、操作顺序、断言点、截图路径、Network/Console 证据和工具限制。
5. 同一项目后续复测优先复用已固化流程；只有页面版本、文案、权限、租户或数据边界变化时才重新勘测。

## Playwright/Cypress 边界

适合：长期稳定回归、CI gate、复杂断言、多页面流程、视觉截图对比。

不适合：一次性轻量冒烟、依赖用户真实登录态的临时验收；也不适合作为缺少 UI 自动化工具时的默认自动安装项。

## 输出证据

集成测试的浏览器操作至少记录：

- 页面 URL。
- 页面元素勘测结果：字段、按钮、弹窗、列表列名、关键状态文案和稳定选择器/可访问性名称。
- 操作步骤。
- 关键断言文本或状态。
- 截图路径或测试报告。
- Console/Network 异常摘要。

UI 视觉比对至少记录：

- 设计稿来源（Figma 链接/设计稿文件路径/版本）。
- 比对页面 URL。
- 比对范围（布局/色彩/字体/响应式/组件状态）。
- 比对工具。
- 差异清单（位置/尺寸/色差/缺失元素）。
- 截图或差异标记图。

## 执行约束

- Playwright/Cypress 这类会启动本地 webServer 或构建进程的 UI e2e 默认串行执行，不要与另一个 UI e2e 命令并行。
- 如果出现 `Another next build process is already running`，先确认没有并发 e2e/build 进程，再重跑。
- 在 workspace 子包中执行 Playwright，优先使用 package script，例如 `pnpm --filter web run e2e -- <spec>`；不要假设 `pnpm --filter web exec playwright` 一定能解析到二进制。
