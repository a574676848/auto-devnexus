# 上游资产（Vendored Upstream Assets）

本目录原样收录三个上游项目的完整素材与脚本，目的是让 `frontend-ui-ux` 的标志设计、示意产品界面、手绘插画三条线**跑出与上游一致的效果**，而不是只保留方法摘要。

| 目录 | 上游仓库 | 收录提交 | 许可 | 规模 |
| :--- | :--- | :--- | :--- | :--- |
| `logo-design-skill/` | [kaankiziltug/logo-design-skill](https://github.com/kaankiziltug/logo-design-skill) | `bbf31e5` | MIT，Copyright 2026 kaankiziltug | 1,565 文件 / 13.3 MB |
| `stageshow/` | [benjitaylor/skills](https://github.com/benjitaylor/skills) 的 `stageshow/` | `299140f` | MIT，Copyright 2026 Benji Taylor（app-icons 与品牌素材不在其内） | 372 文件 / 2.3 MB |
| `handraw-style/` | [yang0/handraw-style](https://github.com/yang0/handraw-style) | `ab848eb` | MIT 附加署名要求（作者 yang0） | 1,065 文件 / 56.3 MB |

除 `.git`、`.github`、`node_modules`、`dist`、`.DS_Store` 外，目录结构与文件内容均与上游一致，保证相对路径引用（`assets/library`、`images/`、`kit/`）不失效。

---

## 1. `logo-design-skill/`：标志参考库与全套脚本

```
logo-design-skill/
  LICENSE
  skills/logo-design/
    SKILL.md                      # 上游原始作业手册（本文档的上游来源）
    references/                   # 14 份：principles / mark-types / svg-construction / testing-checklist …
    scripts/                      # 9 个纯标准库 Python
    templates/                    # 展示板 spec 与品牌规范模板
    assets/library/               # 1,432 个真实标志 SVG + catalog.json + classifications.json + gallery.html
```

| 脚本 | 用途 | 依赖参考库 |
| :--- | :--- | :--- |
| `search_library.py` | 按类型/技法/几何/行业/情绪/主色检索 1,432 个真实标志，`--summary` 看品类惯例，`--exemplary` 只取范例，`--format paths` 直接给文件路径 | 是 |
| `preview_sheet.py` | HTML 测试页（尺寸阶梯、16/32 px、多背景、单色、模糊、镜像、favicon/App 图标/页头情境）；`--refs-industry` 做竞品货架对比 | 部分（`--refs-industry`） |
| `svg_audit.py` | 结构体检与 0 到 100 分就绪度 | 否 |
| `render_png.py` | SVG → PNG，自动挑渲染器（cairosvg / rsvg-convert / Inkscape / Chrome），可截图 HTML、生成 favicon.ico | 否 |
| `export_variants.py` | 黑白单色、方形、favicon、App 图标、`--web-icons` 整套 Web 图标 | 否 |
| `concept_sheet.py` | 概念总览单图（大图 + 64/32/16 px + 一句话 + 推荐），检查点专用 | 否 |
| `presentation_board.py` | 客户提案展板（Brief、每案 + 6 个行业样机、对比、推荐），`--png-dir` 导出幻灯片 | 否 |
| `build_catalog.py` | 维护者工具：重建参考库目录 | 是 |
| `svglib.py` | 公共解析与几何库 | 否 |

Windows 上 `python3` 常是应用商店占位程序，一律用 `python`。示例（在任意工作目录执行，路径写全）：

```bash
python vendor/logo-design-skill/skills/logo-design/scripts/search_library.py --list-values
python vendor/logo-design-skill/skills/logo-design/scripts/search_library.py --industry developer-tools --summary
python vendor/logo-design-skill/skills/logo-design/scripts/search_library.py --technique negative-space --exemplary --format paths
python vendor/logo-design-skill/skills/logo-design/scripts/preview_sheet.py a.svg b.svg --refs-industry ai-ml -o preview.html
python vendor/logo-design-skill/skills/logo-design/scripts/concept_sheet.py a.svg b.svg c.svg --names A B C --notes "…" "…" "…" --recommend 1 --greyscale -o concepts.png
python vendor/logo-design-skill/skills/logo-design/scripts/presentation_board.py spec.json -o board.html --png-dir slides
```

**可用行业值**（`--industry`，写错不会报错但会 0 命中）：`ai-ml`、`cloud-infrastructure`、`database-data`、`design-creative`、`developer-tools`、`ecommerce-retail`、`education`、`finance-banking`、`framework-library`、`gaming`、`hardware-devices`、`health`、`hosting-cdn`、`marketing-analytics`、`media-entertainment`、`open-source-community`、`os-platform`、`other`、`payments-fintech`、`productivity-collaboration`、`programming-language`、`security-identity`、`social-communication`、`testing-monitoring`、`travel-transport`。

**可用技法值**：`containment`、`negative-space`、`line-monoline`、`gradient`、`color-segments`、`dimensional-shading`、`geometric-construction`、`modular-repetition`、`overlap-transparency`、`hidden-meaning`、`isometric-3d`、`radial-symmetry`、`motion-lines`、`mirror-symmetry`、`arrow`、`letter-substitution`、`stacked-layers`、`bracket-code`、`hand-drawn`、`speech-bubble`、`ligature`、`infinity-loop`、`pixel`、`impossible-figure`。

---

## 2. `stageshow/`：React 套件 + 30 多个黄金范例

```
stageshow/
  SKILL.md          # 上游作业手册
  NOTICE.md         # 第三方素材与商标声明（务必保留）
  kit/              # 舞台、窗口、手机、气泡、图表、光标、动效组件，各自带 CSS
  examples/         # 30+ gold、产品研究、教学对照、specimen
  playground/       # 本地预览（vite）
  references/       # 15 份：framing / craft / motion / rehearse / verify / kit / teaching …
  scripts/          # dev.mjs、film.mjs（录制）、class-clash.mjs
  package.json
```

首次使用安装依赖（`node_modules` 不入库）：

```bash
cd vendor/stageshow
npm install
npm run dev        # Windows 打开它打印的 http://127.0.0.1:5173
npm run typecheck  # tsc 检查
npm run build      # 构建 playground 到 dist（构建产物不入库）
```

录制与自检：

```bash
node scripts/film.mjs "<preview>/?capture=<example>" --select '#example' --still --out gold.png
```

用法口径：`kit/` 是 React 组件库，拷进目标项目后 `import { Stage, Window, type Act } from './kit'`；`examples/` 里的每个目录都是一个完整起点，连结构一起拷走再替换成目标产品的 token、图标与文案。`film.mjs` 走 `playwright-core`，需要本机有可用的 Chrome/Chromium。

---

## 3. `handraw-style/`：370 种画风 + 170 种版式 + 36 种主题色

```
handraw-style/
  SKILL.md              # 上游总说明
  STYLES.md            # 370 种画风完整图鉴（含每种的核心特征）
  LAYOUTS.md           # 170 种版式图鉴（SC/IG/SB/IP/EC）
  COLORS.md            # 36 种经典单色
  images/              # 672 个 webp：画风预览 + 版式预览（46 MB）
  skills/handdraw-style-prompter/
    SKILL.md           # 核心子技能手册（27 KB）
    gallery/           # index.html 画风图册、layouts.html、colors.html + 缩略图索引
    references/        # styles.json（370 画风）/ layouts.json（170 版式，含提示词正文）/ colors.json（36 色）/ model_capabilities.json
    scripts/           # prompt_style.py、resolve_reference.py、validate_library.py 等 18 个
    layouts/           # （上游按个人工作流忽略，未随仓库发布）版式定义以 references/layouts.json 为准
```

```bash
python vendor/handraw-style/skills/handdraw-style-prompter/scripts/prompt_style.py --style 18 --theme "秋天的第一杯奶茶"
python vendor/handraw-style/skills/handdraw-style-prompter/scripts/prompt_style.py --layout SC-001 --style 18 --color C-15 --theme "…"
python vendor/handraw-style/skills/handdraw-style-prompter/scripts/prompt_style.py --auto --theme "…"
python vendor/handraw-style/skills/handdraw-style-prompter/scripts/resolve_reference.py --model gpt-image-2 --style 18
```

Windows 控制台先执行 `chcp 65001`（或 `[Console]::OutputEncoding=[Text.UTF8Encoding]::new()`），否则中文提示词会显示成乱码，文件内容本身是 UTF-8 不受影响。

图册浏览：直接打开 `skills/handdraw-style-prompter/gallery/index.html`（画风）、`layouts.html`（版式）、`colors.html`（配色）。重建图册需要 `pip install -r requirements.txt`（Pillow、PyYAML），只有做图库维护时才需要。

---

## 4. 许可与再分发

- 三份上游许可原文分别保留在各目录的 `LICENSE`；`stageshow/NOTICE.md` 与 `kit/brands/SOURCES.md` 逐文件记录了第三方素材来源。
- `handraw-style` 为 MIT **附加署名要求**：任何使用、修改、分发或商业化都必须保留原作者 **yang0** 与仓库链接 `https://github.com/yang0/handraw-style` 的署名。本文件与 `references/handdrawn-style-prompting.md` 均已声明，删除即违约。
- `stageshow/assets/app-icons.ts` 与 `kit/brands/` 中的第三方标志归各自所有者，仅作示例引用；不得把它们当作自有素材对外分发或用于商标性使用。
- `logo-design-skill/assets/library/` 里 1,432 个标志都是各公司的注册商标，只用于研究、比对与货架测试，绝不描摹、改名或再分发为自有标志。

---

## 5. 升级方式

```bash
git clone https://github.com/kaankiziltug/logo-design-skill /tmp/up-logo
git clone https://github.com/benjitaylor/skills /tmp/up-benji
git clone https://github.com/yang0/handraw-style /tmp/up-handraw
```

用 robocopy（Windows）或 rsync 覆盖对应目录，排除 `.git`、`.github`、`node_modules`、`dist`，然后更新本文件顶部的收录提交号。升级后至少回归一次：`search_library.py --list-values`、`npm run typecheck`、`prompt_style.py --style 18 --theme 测试`。

---

## 6. 本仓库对上游做过的唯一改动

- 仅一处：`handraw-style/skills/handdraw-style-prompter/scripts/prompt_style.py` 顶部加了 8 行 Windows 控制台 UTF-8 兜底（`sys.stdout.reconfigure`），否则 `--auto` 在 GBK 控制台会因 💡 抛 `UnicodeEncodeError`。逻辑与输出内容未动。
- 版式模板不依赖 `layouts/` 目录（上游本身也未发布该目录），`prompt_style.py --layout SC-001` 直接读 `references/layouts.json`，已实测可用。
