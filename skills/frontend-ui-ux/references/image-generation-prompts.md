# 界面视觉原型与分段生图系统指南 (UI ImageGen & Prototyping)

## 1. Web 界面分段生图硬法则 (Section-by-Section Rule)

为彻底解决 AI 生图时“文字太小无法阅读、细节模糊无法提取、全页压缩变形”的通病，强制执行以下铁律：

### 核心契约
1. **1 Section = 1 张独立横屏图 (16:9 或 16:10)**。
2. **严禁拼接压缩**：严禁把整站 8 个 Section 压缩进 1 张长图或拼贴画。
3. **连续顺序交付**：多 Section 任务按顺序逐张输出（如：`Section 1 of 6: Hero`, `Section 2 of 6: Features`...）。
4. **拒绝裁剪旧图**：若需局部特写，重新独立生成高清特写图，严禁从全局大图截取模糊碎片。

> 本节只管**界面原型**。文章封面、海报、组图、信息图、漫画、IP 与电商图属于插画资产，走另一套编号化方法（画风编号 + 版式编号 + 主题色、纯图与图文双模式、垫图隔离与改图重绘指令），见 `handdrawn-style-prompting.md`，不要用界面分节规则去套插画。

---

## 2. Web 界面构图锚点与背景模式矩阵

### 2.1 构图锚点 (Composition Anchors)
打破千篇一律的“左文右图”AI 刻板印象，在不同 Section 轮换使用：
- **Centered Statement (居中宣言)**：大字居中，底部双 CTA，全宽背景衬底。
- **Bottom-Left over Canvas (左下文本覆图)**：文字沉底左下，主体资产占据右上视口。
- **Off-Grid Editorial Offset (非对称杂志排版)**：左右列高低错位，大面积留白。
- **Stacked Center (极简堆叠)**：微标签 + 短标题 + 细 CTA 全部居中，极简克制。
- **Right-Text / Left-Image (反向经典)**：左侧视觉资产，右侧文本阐述。

### 2.2 背景模式 (Background Modes)
- **Full-bleed Atmospheric Canvas**：全宽沉浸式调色摄影 + 优雅渐变蒙版（确保文字极高对比度）。
- **Tactile Matte Surface**：细微纸质/胶片颗粒底纹 + 实体机加工质感。
- **Editorial Side-Image (50/50 或 60/40)**：纯色面板与全高图片拼合。
- **Solid Field with Ambient Radial Vignette**：纯深色底搭配极柔和点睛色微光晕。

---

## 3. Mobile 移动端原型生图规范

### 3.1 手机真机框架标准 (Phone Mockup Standard)
- **默认呈现真机框架**：移动端界面默认呈现于精致的 iPhone 或现代旗舰机框架内，四周保留匀称边距。
- **内容主导**：边框起到场景衬托作用，视觉重心始终在屏幕内的 UI 布局本身。
- **严禁页面型 App**：App 必须体现原生特性（状态栏安全区、底部 TabBar、原生 Sheet 抽屉），严禁画成缩放版网页。

### 3.2 多屏原型流一致性契约 (Multi-Screen Flow)
多屏输出必须严格共享一套设计圣经：
- **同一调色盘**：主色、点睛色与中性色严格一致。
- **同一字阶与圆角系统**：标题、正文、卡片与按钮圆角完全同构。
- **逻辑流顺畅**：Onboarding 引导 → Auth 认证 → Home 首页 → Detail 详情 → Checkout 结算。

---

## 4. 结构化生图 Prompt 模板

### Web Section Prompt 范式
```text
High-end desktop UI design for [BRAND/PRODUCT NAME], Section: [SECTION NAME].
Style: Premium, intentional, [STYLE_MODE], 16:9 horizontal web section.
Composition: [COMPOSITION_ANCHOR], generous whitespace, breathable rhythm.
Background: [BACKGROUND_MODE], controlled contrast.
Typography: [FONT_MOOD], tight tracking, max 2 lines for headline, perfectly readable.
Color Palette: Dominant [BASE_COLOR], accent [ACCENT_COLOR], neutral [NEUTRAL_SCALE].
UI Elements: [KEY_COMPONENTS], bespoke double-bezel cards, tactile button-in-button CTA.
Quality Bar: Awwwards Site of the Day tier, no generic AI blobs, no purple neon glow, no messy collages.
```

### Mobile Screen Flow Prompt 范式
```text
Premium mobile app interface for [APP NAME], Screen: [SCREEN NAME / FLOW STEP].
Platform: [iOS native / Android Material], presented inside a sleek, subtle iPhone mockup with even margins.
Composition: Clean safe-area hierarchy, uncluttered header, focused primary action.
Typography: Crisp mobile type scale, high contrast, comfortably readable labels.
Color & Surface: [PALETTE_SPEC], tactile surface with subtle grain, consistent with the app design system.
Components: [TAB_BAR / CARDS / SEGMENTED_CONTROLS / SHEET], bespoke icon set.
Quality: App Store featured editorial standard, zero generic fintech charts, zero fake complexity.
```
