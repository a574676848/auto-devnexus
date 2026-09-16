---
name: dev-test
description: 测试统一入口 skill。识别用户测试意图后路由到对应子执行手册（AGENT.md）。覆盖：写用例、冒烟、集成/e2e、UI 视觉、bug 回归、bug 增量冒烟/集成/UI。当用户提到"测试、写用例、冒烟、集成测试、e2e、UI 视觉、bug 回归、bug 验证、修复验证、增量测试、补测试、覆盖矩阵"等任意测试相关请求时触发。不处理：代码审查（review）、安全审计（security-review）、性能压测、负载测试。
---

# Dev Test — 测试统一路由入口

本 skill 是 `skills/dev-test/` 下所有测试执行手册的统一路由入口。
负责意图识别、上下文加载、分发执行。子目录的 `AGENT.md` 不会被 Claude Code 单独注册为 skill，必须由本入口主动读取并执行。

---

## 执行协议（强制顺序）

每次触发本 skill，必须严格按以下顺序执行，**每步开始前输出状态声明，完成后输出结果声明**。

---

### Step 1 — 加载内核

**开始声明**：
```
[dev-test] ⏳ Step 1/4 加载测试治理内核...
```

读取 `skills/dev-test/test-governance-core/AGENT.md`，作为本轮所有测试任务的公共底座。
内核包含：上下文发现、技术栈识别、知识库降级、用例 schema、真实环境阻断、增量优先、报告口径。

> ⚠️ **真实环境硬约束**：内核要求所有测试默认使用真实环境、真实账号、真实服务、真实数据。缺失任一必要信息时，必须**暂停执行并主动向用户追问缺失项**（明确说出缺什么、为什么需要、用户应如何提供），**等用户补齐后再继续**当前流程；不得直接退出、不得只丢一份"待澄清清单"了事、不得用 mock / dry-run / 单测 / 离线模式替代真实验证。本入口在路由前必须把这条约束传递给被调用的执行手册。
>
> ⚠️ **操作与编码硬约束**：除冒烟测试外，其他测试场景必须模拟人工操作执行验证，覆盖真实浏览器、真实客户端、真实 CLI 或等价用户路径；接口调用只能作为辅助证据，不得作为唯一验证方式。所有命令、脚本、报告、日志和证据文件的输入输出必须统一使用 UTF-8 编码。

**完成声明**：
```
[dev-test] ✅ Step 1/4 内核加载完成
```

---

### Step 1.5 — BrowserSkill 健康检查（仅当本轮涉及浏览器操作时）

**触发条件**：路由命中以下任一项时强制执行：
- `ui-tester`（视觉比对）
- `bug-ui-delta-tester`（UI bug 增量验证）
- `integration-tester` 且本轮包含浏览器交互（导航 / 点击 / 表单 / 读页面 / 截图等）

**开始声明**：
```
[dev-test] ⏳ Step 1.5 检测到浏览器意图，正在校验 BrowserSkill...
```

**执行**：
```bash
bsk doctor
```

**结果路由与声明**：

| 观察到 | 状态声明 | 处理方式 |
|---|---|---|
| `bsk doctor` 返回无 `fail` 且扩展已连接 | `[dev-test] ✅ Step 1.5 BrowserSkill 健康，继续执行` | 进入 Step 2 |
| `command not found` / `bsk` 不可用 | `[dev-test] ⚠️ Step 1.5 BrowserSkill 未安装，等待用户确认...` | 主动告知 + 询问是否安装 + 用户确认后执行 `irm https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.ps1 | iex`，再运行 `bsk doctor` |
| `bsk doctor` 报告 daemon 未运行 | `[dev-test] ⏳ Step 1.5 BrowserSkill 守护进程未启动，正在启动...` | 按 doctor 输出的提示启动或重试 `bsk doctor`，不得猜测进程路径 |
| `bsk doctor` 报告扩展未连接 | `[dev-test] ⚠️ Step 1.5 浏览器扩展未连接，等待用户操作...` | 引导用户安装 Chrome/Edge 扩展并在扩展弹窗确认连接 |
| 用户拒绝安装 | `[dev-test] ℹ️ Step 1.5 已跳过 BrowserSkill，启用降级方案` | 项目已有 Playwright/Cypress 时复用，否则只生成手工步骤清单，明确告知限制范围 |
| 更深层故障 | `[dev-test] ❌ Step 1.5 BrowserSkill 故障，转交专项排查` | 引导用户参考 https://github.com/Tencent/BrowserSkill 的 AGENT_INSTALL.md 和 README.md |

> ⚠️ **安装属于中等风险动作，必须等用户明确确认后才执行**。不得未经同意直接拉取并执行远程脚本。

详细引导流程见 `test-governance-core/references/ui-tooling.md` → "BrowserSkill 缺失时的引导流程"。

---

### Step 2 — 意图识别与路由

**开始声明**：
```
[dev-test] ⏳ Step 2/4 识别测试意图...
```

按下述"路由判定规则"识别用户意图。

**完成声明**（路由确定后输出）：
```
[dev-test] ✅ Step 2/4 路由确定：识别意图 <X>，加载执行手册 <path/AGENT.md>
```

若触发歧义澄清，输出：
```
[dev-test] ⚠️ Step 2/4 意图存在歧义，等待用户确认...
```
等用户确认后再输出路由完成声明。

若触发多重意图队列，输出：
```
[dev-test] ℹ️ Step 2/4 检测到多重意图，队列：A → B → C
```

---

### Step 3 — 执行测试手册

**开始声明**：
```
[dev-test] ⏳ Step 3/4 开始执行：<手册名称>
```

按路由结果读取对应的 `AGENT.md`，把内核约束 + 用户原始上下文 + 手册流程合并执行。

手册内部每个子步骤也需输出状态，格式：
```
[dev-test] ⏳ <手册名> / <子步骤描述>...
[dev-test] ✅ <手册名> / <子步骤描述> 完成
[dev-test] ⚠️ <手册名> / <子步骤描述> 需要用户补充信息，等待中...
[dev-test] ❌ <手册名> / <子步骤描述> 失败：<原因>
```

多重意图队列中，每个手册执行前额外输出进度：
```
[dev-test] ▶ 队列进度：正在执行 2/3 — <手册名称>
```

**完成声明**：
```
[dev-test] ✅ Step 3/4 <手册名称> 执行完成
```

若执行被阻断（真实环境信息缺失）：
```
[dev-test] ⏸ Step 3/4 执行已暂停，等待用户补充：<具体缺失项>
```

---

### Step 4 — 产出落盘

**开始声明**：
```
[dev-test] ⏳ Step 4/4 正在写入报告和证据...
```

按内核要求输出报告到被测项目的 `test-governance/reports/`，证据落 `test-governance/evidence/`，默认增量不覆盖。

**完成声明**：
```
[dev-test] ✅ Step 4/4 产出落盘完成
  📄 报告：test-governance/reports/<文件名>
  🗂 证据：test-governance/evidence/<路径>（如有）
```

**全流程结束声明**：
```
[dev-test] 🏁 测试任务完成 | 手册：<名称> | 状态：<通过/失败/阻断> | 报告：<路径>
```

---

## 路由判定规则

### 第一判定：是否涉及 Bug 实体

**判定 Bug 系列的硬条件**（满足任一即为 Bug 系列）：

- 用户给出具体 bug 描述、症状、报错日志、截图、复现步骤
- 用户提供修复 diff / commit / PR 链接，明确说"修复了 X 问题"
- 用户引用 bug 编号 / Jira 工单号 / issue 链接
- 用户说"复现、回归、修复后验证、防回归"且指向具体故障

**仅"我刚改了代码、帮我测一下"不算 Bug 系列**——这是常规改动测试，按"第二判定"处理。

### 第二判定：测试类型分类

| 用户意图特征 | 路由目标（AGENT.md 路径） |
|---|---|
| **Bug 系列** |  |
| 复现 bug、修复后回归、为 bug 沉淀长期回归用例、防回归资产 | `bug-regression-tester/AGENT.md` |
| bug 修复后跑哪些冒烟、最小启动验证、bug 是否破坏 P0 主流程 | `bug-smoke-delta-tester/AGENT.md` |
| bug 影响哪些接口、修复后接口联调、服务协作受影响范围 | `bug-integration-delta-tester/AGENT.md` |
| bug 修复后页面验证、UI bug 回归、视觉/交互受影响 | `bug-ui-delta-tester/AGENT.md` |
| **常规系列** |  |
| 写测试用例、补测试清单、生成测试场景、覆盖矩阵、单元测试用例设计 | `test-case-writer/AGENT.md` |
| 冒烟测试、发布前快速检查、服务可用性、健康检查 | `smoke-tester/AGENT.md` |
| 集成测试、接口联调、服务协作、模块集成、e2e、UAT、端到端 | `integration-tester/AGENT.md` |
| UI 视觉验证、设计稿比对、像素级对比、视觉回归、Figma 比对 | `ui-tester/AGENT.md` |
| **内核直调** |  |
| 用户明确说"治理规则、测试框架配置、知识库接入策略、报告口径" | `test-governance-core/AGENT.md`（直接执行） |

### 第三判定：歧义澄清

碰到下列高频歧义场景时，**先停下来询问用户**，不要默认选一个：

| 歧义场景 | 必须澄清的问题 |
|---|---|
| "修复后验证一下" | 只跑最小冒烟（bug-smoke-delta）还是要沉淀长期回归资产（bug-regression）？ |
| Bug 同时触及接口和页面 | 只跑接口集成增量（bug-integration-delta），还是同时跑 UI 增量（bug-ui-delta）？ |
| "完整测一遍" | 串行跑：smoke → integration → ui？还是只挑核心路径？ |
| "测一下我刚改的代码" | 你想要：(a) 写用例 (b) 跑冒烟 (c) 跑集成 (d) 跑 UI？ |
| 用户给了 bug 描述但没说测试类型 | 你想要：(a) 复现 + 回归资产 (b) 增量冒烟 (c) 增量集成 (d) 增量 UI？ |

### 第四判定：多重意图串联

用户一次说多个意图（"补回归 + 跑增量冒烟"、"先写用例再跑集成"）时：

1. 拆成有序队列，按用户表述顺序执行
2. 每个子手册独立产报告，但合并写入同一份 `test-governance/reports/<日期>-combined.md`
3. 任一子手册触发真实环境阻断，整条队列停止，输出统一阻断报告
4. 队列开始前向用户播报：`[dev-test 队列] 将依次执行：A → B → C`

### 第五判定：超出范围

下列请求**不接**，直接告诉用户走对应专业 skill：

| 请求 | 引导 |
|---|---|
| 代码审查 / Review | 用 `/review` 或 review skill |
| 安全审计 / 漏洞扫描 | 用 `/security-review` 或 security-review skill |
| 性能压测 / 负载测试 / 基准测试 | 不在 dev-test 覆盖范围，建议接专门的压测工具（k6 / JMeter / wrk） |
| 部署验证 / 灰度回滚 | 不在 dev-test 覆盖范围 |

---

## 子手册一览（用于兜底询问）

当意图无法匹配任何路由规则时，向用户展示下表并请用户选择：

| 手册 | 一句话说明 | 适用场景 |
|---|---|---|
| `test-case-writer` | 生成结构化测试用例矩阵 | 没用例 / 用例不全 / 需要覆盖矩阵 |
| `smoke-tester` | 最小可用性冒烟 | 发布前 / 联调前 / 快速健康检查 |
| `integration-tester` | API / 服务 / DB 模块协作验证（含 e2e） | 接口联调 / 跨服务契约 / 端到端 |
| `ui-tester` | 设计稿与实际 UI 视觉比对 | Figma 对比 / 视觉回归 |
| `bug-regression-tester` | bug 复现 + 修复后回归 + 沉淀资产 | 长期防回归 / Jira 工单收尾 |
| `bug-smoke-delta-tester` | bug 修复后最小冒烟 | 改动小 / 想确认没破坏启动 |
| `bug-integration-delta-tester` | bug 修复后最小集成 | 改动触及接口或服务协作 |
| `bug-ui-delta-tester` | bug 修复后最小 UI 验证 | 改动触及页面 / 组件 / 交互 |

---

## 约束

- 本 skill 只做路由 + 内核加载 + 队列编排，不重复实现子手册逻辑。
- `test-governance-core/AGENT.md` 是公共前置内核，每次路由前必须加载；不作为常规路由目标，除非用户明确要"看治理规则"。
- 路由后完整传递用户原始上下文，不裁剪、不改写。
- 子目录已统一改名为 `AGENT.md`，Claude Code 不会单独注册它们；本入口是唯一触发点。
- 真实环境阻断是底线：缺信息就停下问，不许用 mock / dry-run / 离线模式包装成"测试通过"。
- 非冒烟测试必须模拟人工操作：集成、e2e、UAT、UI 功能、回归和 bug 增量验证不得只做接口调用，必须保留真实用户路径证据。
- 编码是底线：所有输入输出、脚本、日志、报告和证据文件必须使用 UTF-8。
