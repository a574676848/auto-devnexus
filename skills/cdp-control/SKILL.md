---
name: cdp-control
description: 用 Chrome DevTools Protocol 跨平台驱动并取证任意 Chromium 内核界面（Windows / macOS / Linux 上的 WebView2、Tauri、Electron 桌面窗口，Chrome、Edge 与无头 Chromium）。当任务需要真机验证界面、点击或输入、按键滚动、读回 DOM 与运行时状态、截图取证、给宿主开调试端口、或在没有 Playwright/Selenium 的环境里操作界面时使用。凡出现 remote-debugging-port、WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS、/json/list、Runtime.evaluate、Input.dispatchMouseEvent、DevTools 协议、9333 或 9222 端口、CDP 等字样，或长官说“验证界面上真的变了”“点一下这个按钮”“看看窗口现在什么样”“这台机器上的界面跑一遍”，都应先加载本 Skill。不适用：需要长官已登录态与浏览器扩展的场景用 browser-skill。
---

# CDP 通用控制与取证

一套连上任意 Chromium 调试端点、看清页面、派发真实交互、再用可复核证据收口的方法。
适用宿主：WebView2 / Tauri / Electron 桌面窗口、Chrome、Edge、无头 Chromium，三平台同构。

统一驱动：`<skill>/scripts/cdp.py`（下称 `cdp.py`）。**纯 Python 3.8+ 标准库，零依赖、零 pip 安装**，
Windows / macOS / Linux 上跑的代码完全一致。协议细节看 `references/protocol.md`，
给宿主开端口看 `references/hosts.md`，遇到怪现象先查 `references/cases.md`。

`scripts/` 下四个文件，`cdp.py` 是入口，其余是它 import 的同目录模块，**必须整体保留**：

| 文件 | 职责 |
|---|---|
| `cdp.py` | CLI 入口：参数解析、各子命令、输出契约 |
| `cdpui.py` | 页面级操作：定位器、点击、输入、求值、候选枚举 |
| `cdpws.py` | 传输层：HTTP 端点、目标选择、WebSocket 分帧 |
| `cdpai.py` | 可选的 Laya 语义判定桥（配置解析、代理绕过、请求封装） |

## 运行前置

只要一个 Python 3.8+ 解释器。选命令名的规则：

| 平台 | 用哪个 |
|---|---|
| macOS / Linux | `python3` |
| Windows | `python`（没装就用 `py -3`） |
| 都没有 | 先装 Python 3，或走 `references/cases.md` 末尾的 Node 逃生通道 |

本文其余部分统一写作 `python3`，在 Windows 上把它读作 `python` 即可。

## 契约：只认前缀，不认退出码

`cdp.py` 每次运行只输出一行：

```text
OK:<裸字符串或紧凑 JSON>
ERR:<错误码>:<说明>
```

之所以不让退出码承载判定，是因为这条链路上每一层都可能把失败吞掉——WebSocket 的对端关闭、
页内 JS 的异常返回、HTTP 层的中断，都不必然改变进程退出码，而反过来一次**已经成功**的动作也可
能被客户端误报成失败（`/json/close` 返回的是纯文本 `Target is closing`，按 JSON 解析就会把成功
读成失败）。把判定收敛到唯一一个显式前缀上，验证结论才不会自欺。
**断言 `OK:` 前缀，否则等于没验证**，并且要看 payload 里的字段本身（`count`、`value`、`deep`），
不要只看有个 `OK:` 就当成功。

默认恒以退出码 0 收尾；需要在 shell 里串联时加 `--strict-exit`，它会在 `ERR:` 时返回 1。

## 命令清单

这是全部命令，不要臆造其它名字。完整参数看 `python3 cdp.py <命令> --help`。

| 命令 | 关键参数 | 作用 |
|---|---|---|
| `info` | | 端点存活、浏览器与协议版本 |
| `targets` | `--target-type` `--url-match` | 列出调试目标 |
| `eval` | `-e` \| `-E`、`--user-gesture`、`--no-await`、`--max-chars` | 求值并打印返回值 |
| `click` | `-s`、`--text`、`--index`、`--force` | 滚动到位、命中测试、真实鼠标序列 |
| `type` | `-s` `-t`、`--clear`、`--submit` | 聚焦、清空可选、插入文本、可回车 |
| `key` | `-k`、`--modifiers`、`-s` | 派发按键（Enter/Escape/Tab/方向键/单字符） |
| `wait` | `-s` \| `-e`、`--gone`、`--timeout`、`--poll-ms` | 页内轮询直到条件成立 |
| `text` | `-s` | 元素的 innerText |
| `html` | `-s` | 元素的 outerHTML |
| `shot` | `-o`、`--full-page`、`--width` `--height` | 截图落盘（可带视口覆盖） |
| `nav` | `-u` | 导航并等 `readyState` 到 complete |
| `open` | `-u` | 新开标签页，返回新目标 id |
| `close` | `--target-id` | 关闭目标 |
| `pick` | `-s`、`--intent`、`--click`、`--limit`、`--min-margin` | 用语义判定在候选元素里选一个（**可选，需 Laya**） |
| `judge` | `--question`、`--type`、`--criteria`、`--context-selector` | 对当前页面状态问一道校准题（**可选，需 Laya**） |
| `laya-health` | | 检查 Laya 服务连通性（不需要浏览器目标） |

选择目标的参数（除 `info`/`targets`/`open`/`close` 外都适用）：
`--port`、`--url-match`、`--target-id`、`--target-type`、`--first`、`--ws-url`。

## 四步闭环

```text
连接  ->  观察  ->  动作  ->  复验
```

每一步都有可执行手段，不要凭想象跳过任何一步。

### 第一步：拿到端点

调试端口必须在**宿主启动之前**给出，进程已经在跑时再设环境变量不会有任何效果——这是最常见的白费功夫。
宿主各自的开端口方式见 `references/hosts.md`，最常见的一条：

```bash
# macOS / Linux
WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS='--remote-debugging-port=9333' ./your-app
```

```powershell
# Windows (PowerShell)
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9333'
# 然后才启动桌面端
```

确认端点活着：

```bash
python3 cdp.py info                 # 端口、浏览器版本、协议版本
python3 cdp.py targets              # 列出全部目标
```

`--port` 省略时会自动探测 9333 / 9222 / 9229 / 9444 / 9223 / 8315；命中 `ERR:no-endpoint` 说明
端口根本没开，回去检查启动参数与端口占用，不要瞎试方法。

### 第二步：钉住目标并观察

**多标签时先钉目标再动手。** `/json` 的返回顺序会随标签页开合而变，`open` 新开一个标签就可能让
"第一个 page" 从 A 变成 B，后续所有操作静默打到错误的窗口上。所以只要端点上可能不止一个页面：

```bash
python3 cdp.py targets --target-type page
python3 cdp.py eval --url-match "your-app" -e "document.title"
```

脚本在"多个目标都匹配且没有指定 `--url-match`/`--target-id`"时会直接报
`ERR:ambiguous-target` 并列出候选，而不是替你猜。确实不在乎是哪个时才用 `--first`。

观察用 `eval`。让表达式**返回字符串**最省事，机读就自己 `JSON.stringify`：

```bash
python3 cdp.py eval --url-match "app" -e "document.title"
python3 cdp.py eval --url-match "app" -e "JSON.stringify({rows:document.querySelectorAll('.row').length, busy:!!document.querySelector('.spinner')})"
```

返回 `JSON.stringify(...)` 的结果是必要的：`returnByValue` 把 JS 对象降级成宿主对象后，
中介层经常只能打印出空壳，而字符串能原样穿过所有转义层。

### 第三步：动作

```bash
python3 cdp.py click --url-match "app" -s "button.primary" --text "提交"
python3 cdp.py type  --url-match "app" -s "textarea" -t "你好" --submit
python3 cdp.py key   --url-match "app" -k Escape
python3 cdp.py nav   --url-match "app" -u "https://example.com"
```

为什么不用更省事的 `element.click()` / `node.value = x`：真机实测过这两条捷径都会骗人。
`element.click()` 只派发 click 监听，跳过 pointerdown、hover、焦点转移与框架的合成事件链，
React / Vue / Tauri 这类宿主常在这条链上才真正响应；`node.value = x` 对受控组件完全无效——
页面的回显不变、框架的 state 不变，可脚本却"看起来成功了"。所以 `click` 走真实的
`mouseMoved → mousePressed → mouseReleased → mouseMoved` 序列，`type` 走 `Input.insertText`
（浏览器内部编辑管线，产出真实 `input` 事件），并且写完回读。

`click` 派发前会先把元素滚到视野中央，并在**元素自己所在的 root**（含 Shadow DOM）内做命中测试；
如果中心点被别的节点盖住，会返回 `ERR:occluded` 并告诉你盖住它的是谁。这时正确做法是先把遮挡
处理掉（关掉弹窗、切到正确的层），而不是加 `--force` 硬点——硬点只会点到遮罩上，然后你会以为
按钮坏了。

### 第四步：复验与取证

动作之后**必须**再看一眼，且要看真实状态而不是脚本回执：

```bash
python3 cdp.py wait --url-match "app" -s ".result" --timeout 15000
python3 cdp.py eval --url-match "app" -e "document.querySelector('.result').textContent"
python3 cdp.py shot --url-match "app" -o ./evidence/after.png
```

`wait` 在页内轮询（单次往返），比"睡两秒再看"既快又可复现；`--gone` 用来等某个元素消失。
要给人看的证据用 `shot`，`--full-page` 抓整页，`--width/--height` 用来验响应式布局。

## 可选增强：Laya 语义判定

选择器与文本匹配搞不定时（类名是哈希、UI 被本地化、五个按钮长得一样），可以在配好 Laya 服务后
用 `pick` 在候选元素里做一次带概率的选择，或用 `judge` 对页面状态问一道校准题。**没有 Laya，
前面所有能力照常工作**，它只是可选的语义助手。

```bash
python3 cdp.py laya-health                                  # 先确认服务通
python3 cdp.py pick --url-match "app" -s "form button" --intent "提交当前表单" --click
python3 cdp.py judge --url-match "app" --question "表单是否已提交成功？"
```

地址与令牌全走环境变量或 `~/.config/cdp-control/laya.json`，脚本里不写死任何服务地址。
用法、字段含义、**以及它实测的边界（对提示构造高度敏感、领先幅度普遍只有 0.03–0.19、
上下文里没有的证据答不出来）** 都在 `references/laya.md`，用之前请读完它的最后一节。

三条硬性配合要求，因为它不是权威：

- `pick` 的候选池要**先收窄**再用，别拿它扫全页按钮；近义候选两三个时它才靠谱。
- 判定结果只看 `runnerUpMargin`，不要只看 `probability`；`--min-margin` 默认 0.10，
  领先不足时它会直接报错而不是悄悄选错。
- 无论 `pick` 还是 `judge`，**动作之后照旧 `eval` 复验**。冲突时以 `eval` 的真实读数为准。

## 铁律

1. **端口先于进程**。调试参数必须在宿主启动前生效；已运行的进程只能重启，改不了。
2. **先钉目标再动手**。多页面时不指定 `--url-match`/`--target-id` 就是随机操作一个窗口。
3. **只认真实指针与真实输入**。捷径 API 会绕过宿主真正响应的那条事件链。
4. **动作必复验，复验要轮询**。异步渲染的延迟不是用固定 sleep 能覆盖的。
5. **写完读回**。`type` 会回读输入框的值；状态类改动自己再 `eval` 一次读回关键字段。
6. **判定看 `OK:` 前缀与 payload 字段**，退出码不承载任何结论。
7. **遮住就先解决遮挡**，别用 `--force` 掩盖问题。
8. **收尾清场**。验证完清掉调试端口环境变量或关掉专用实例，不要把调试端口带进日常使用。
9. **路径与平台无关**。输出路径用调用方传入的值，不要在脚本或示例里写死盘符、用户目录或某个平台的路径。

## 故障速查

| 现象 | 先查 |
|---|---|
| `ERR:no-endpoint` | 启动参数是否在宿主启动前生效；端口是否被别的进程占用；基址是否 `127.0.0.1` |
| `ERR:no-target` | 窗口是否真的开了；`targets` 看有没有 `type=page`；刚启动时脚本自带重试 |
| `ERR:ambiguous-target` | 用 `--url-match` 或 `--target-id` 钉住；确认不是打到了别的标签 |
| `ERR:occluded` | 弹窗/遮罩/浮层；先关掉它，再点目标 |
| `ERR:no-match` | 选择器是否命中；元素是否在 Shadow DOM 里（`click` 会自动下潜，`eval` 不会）；是否 `display:none` |
| `ERR:eval-exception` | 表达式抛异常；确认选择器存在、字段名拼写正确 |
| `ERR:timeout` | 条件始终为假；用 `eval` 看当前真实状态，别加大超时硬等 |
| `ERR:shot-empty` | 窗口最小化或未合成；先让它可见 |
| `ERR:connect-failed` | 握手被拒或对端关闭；目标是不是已经导航走/关掉了，重新 `targets` |
| eval 返回 `{}` / 空 | 忘了 `JSON.stringify`；或表达式返回 `undefined`；或用了 `--no-await` |
| 点击没反应 | 目标是否被遮挡；是否点到了禁用态；先 `wait` 再点，别立刻点 |
| 终端里中文乱码 | 脚本已把 stdout 固定为 UTF-8 且 JSON 走 `\uXXXX` 转义；若仍乱码是终端代码页问题，落盘文件不受影响 |

更多疑难（iframe、剪贴板与用户手势、文件上传、下载、多窗口、崩溃恢复、无 Python 环境）见
`references/cases.md`。

## 参考文件

| 文件 | 何时读 |
|---|---|
| `references/protocol.md` | 要手写方法调用、判断帧格式、看参数语义与错误结构时 |
| `references/hosts.md` | 要给 WebView2 / Tauri / Electron / Chrome / Edge / 无头 / 远程宿主开调试端口时 |
| `references/cases.md` | 常规手段打不通的疑难场景与排障路径 |
| `references/laya.md` | 要用 `pick` / `judge` 语义判定，或需要 Laya 的配置与实测边界时 |
