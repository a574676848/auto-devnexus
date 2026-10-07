# CDP 协议速查

需要手写方法调用、判断帧格式、或核对参数语义时读本文件。
`cdp.py` 已经把下面绝大多数东西包好了；这里给的是"它为什么这么写"以及"包不住时怎么办"。

## 目录

- [HTTP 面](#http-面)
- [WebSocket 帧格式](#websocket-帧格式)
- [三个最容易踩的解析坑](#三个最容易踩的解析坑)
- [Runtime.evaluate 参数语义](#runtimeevaluate-参数语义)
- [常用方法速查](#常用方法速查)
- [事件订阅规则](#事件订阅规则)
- [坐标系与缩放](#坐标系与缩放)
- [安全边界](#安全边界)

## HTTP 面

基址恒为回环地址（默认 `127.0.0.1`），端口由宿主启动参数决定。

| 端点 | 方法 | 用途 |
|---|---|---|
| `/json/version` | GET | 浏览器版本、协议版本、browser 级 `webSocketDebuggerUrl`。最轻活的存活探针 |
| `/json`、`/json/list` | GET | 目标列表：`id`、`type`、`title`、`url`、`webSocketDebuggerUrl` |
| `/json/new?<url>` | **PUT** | 新建标签页。新版 Chrome 用 GET 会返回 405，必须 PUT |
| `/json/activate/<id>` | GET | 把标签页切到前台 |
| `/json/close/<id>` | GET | 关闭目标 |
| `/json/protocol` | GET | **整份协议 JSON schema**。想知道某方法当前有哪些参数，直接查这里，比翻文档可靠 |

`type` 常见取值：`page`、`iframe`、`worker`、`service_worker`、`background_page`、`browser_ui`、`webview`、`other`。
脚本默认只取 `page`；找 iframe 里的文档才用 `--target-type iframe`。

**列表顺序不稳定**：开合标签页会改变 `/json` 的排列，`[0]` 不构成稳定身份。多目标必须钉 `id` 或匹配 `url`。

**Origin 检查**：Chrome 会拒绝携带未授权 `Origin` 头的 WebSocket 连接，报
`Rejected an incoming WebSocket connection from the <origin> origin`。
非浏览器客户端（.NET `ClientWebSocket`、Node `ws`）默认不发 `Origin`，天然通过；
如果你用浏览器页面里的 JS 去连，就得给宿主加 `--remote-allow-origins=<origin>`。

## WebSocket 帧格式

请求：

```json
{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}
```

成功回执：

```json
{"id":1,"result":{"result":{"type":"string","value":"CDP 靶场"}}}
```

协议级失败（方法名写错、参数结构错）：

```json
{"id":1,"error":{"code":-32601,"message":"'Foo.bar' wasn't found"}}
```

事件（**没有 `id`**）：

```json
{"method":"Page.loadEventFired","params":{"timestamp":12345.6}}
```

业务级异常（表达式抛错）藏在 `result.exceptionDetails`：

```json
{"id":1,"result":{"result":{"type":"object","subtype":"error"},"exceptionDetails":{
  "text":"Uncaught","exception":{"description":"ReferenceError: nope is not defined\n    at <anonymous>:1:1"}}}}
```

## 三个最容易踩的解析坑

1. **事件会插在回执中间。** WebSocket 上事件与回执共用一个通道，绝不能"发一条读一条"就当成回执。
   必须循环读到 `id` 匹配为止；不匹配的帧直接丢弃。这也是 `cdp.py` 里 `_read_message` 与
   `request` 分两层的原因。
2. **大消息会分片。** 单帧可能被拆成多个 WebSocket 分片，底层一次 `recv` 只给一片。
   必须持续读到该消息的 `FIN` 才算拿到完整内容——截图（base64 PNG）、大 DOM 快照都会超出一片。
   分片要累积起来整体解码，不要假设"一次读取 = 一条消息"。
3. **两个层级的错误要分别处理。** `error` 是协议层（方法不存在、参数不合法）；
   `exceptionDetails` 是业务层（页面里那行 JS 抛了）。只判其中一个，另一种失败会被当成空结果吞掉。

## Runtime.evaluate 参数语义

| 参数 | 语义与后果 |
|---|---|
| `expression` | 要执行的 JS。支持 `await`（需要 `awaitPromise`） |
| `returnByValue: true` | **必须显式给**。否则返回的是 `objectId` 句柄，不是一个能直接读的值；句柄还会泄漏，需要 `Runtime.releaseObject` |
| `awaitPromise: true` | 表达式返回 Promise 时等它 settle。忘了它就只能拿到一个 Promise 对象 |
| `userGesture: true` | 让本次求值处在一个"用户激活"上下文里。剪贴板、`window.open`、全屏、文件选择器都要求它 |
| `timeout: <ms>` | 限制 `await` 的等待；不给的话一个永不 settle 的 Promise 会把整条链路挂死 |
| `contextId` / `uniqueContextId` | 指定在哪个执行上下文里求值，操作跨源 iframe 时用它 |

判读结果：`result.result.type` 为 `undefined` 时压根没有 `value` 字段；为 `object` 且给了
`returnByValue` 时会降级成宿主对象。**让表达式 `JSON.stringify(...)` 返回字符串**是最省心的做法，
字符串能原样穿过 JSON 转义、终端编码、宿主语言字符串转换这几层。

## 常用方法速查

**Runtime**：`enable`、`evaluate`、`callFunctionOn`（传 `objectId` 调用函数，适合句柄式操作）、
`getProperties`、`releaseObject`、`compileScript`

**Page**：`enable`、`navigate`、`reload`、`captureScreenshot`（`format`、`captureBeyondViewport`、
`clip`）、`getLayoutMetrics`、`printToPDF`、`addScriptToEvaluateOnNewDocument`、
`handleJavaScriptDialog`、`getFrameTree`、`createIsolatedWorld`

**Input**：`dispatchMouseEvent`、`dispatchKeyEvent`、`insertText`、`dispatchTouchEvent`、
`dispatchDragEvent`、`dispatchMouseEvent{type:'mouseWheel'}`、`setIgnoreInputEvents`

**DOM**：`getDocument`（`pierce: true` 可穿透 Shadow DOM）、`querySelector`、`getBoxModel`、
`describeNode`、`focus`、`setFileInputFiles`、`resolveNode`

**Emulation**：`setDeviceMetricsOverride`、`clearDeviceMetricsOverride`、`setEmulatedMedia`、
`setUserAgentOverride`、`setGeolocationOverride`、`setTimezoneOverride`、`setPageScaleFactor`、
`setEmitTouchEventsForMouse`、`setCPUThrottlingRate`

**Target**：`getTargets`、`attachToTarget`（`flatten: true` 时用 `sessionId` 路由）、`createTarget`、
`closeTarget`、`activateTarget`、`setAutoAttach`

**Network**：`enable`、`getResponseBody`、`setExtraHTTPHeaders`、`emulateNetworkConditions`、
`setBlockedURLs`、`getAllCookies`、`setCookie`

**Browser**：`grantPermissions`、`setPermission`、`getVersion`、`setDownloadBehavior`

**Log / 控制台**：`Log.enable` → `Log.entryAdded`；`Runtime.enable` → `Runtime.consoleAPICalled`

**Debugger**：`enable`、`setBreakpointByUrl`、`paused` 事件、`evaluateOnCallFrame`、`resume`

**Overlay**：`highlightNode`（把某个节点高亮出来，便于人工确认你到底在操作哪一个）

用 `flatten: true` 的 session 模式时，发往子目标的每条消息都要带 `sessionId`，回执与事件也会带回来。
只有需要同时操作多个目标（多标签、iframe、worker）时才值得上这层复杂度；否则一次连一个目标更简单。

## 事件订阅规则

- **事件没有补发**。只有 `enable` 之后发生的才会推给你；连接之前的历史消息拿不到。
- 想抓页面初始化阶段的错误，用 `Page.addScriptToEvaluateOnNewDocument` 注入收集器，再 `Page.reload`。
- 会阻塞渲染进程、导致 `Runtime.evaluate` 永不返回的，务必提前处理：
  `Page.javascriptDialogOpening`（alert / confirm / prompt / beforeunload）→ `Page.handleJavaScriptDialog`。
  这是"脚本突然挂死"的头号原因。

## 坐标系与缩放

- `Input.dispatchMouseEvent` / `dispatchTouchEvent` 的 `x`、`y` 是 **CSS 像素、视口坐标**，
  与 `getBoundingClientRect()` 完全同一坐标系。设备像素比、Ctrl 缩放都不影响它们。
- `Page.captureScreenshot` 输出的**位图**才受 `deviceScaleFactor` 影响：位数会按 DPR 放大。
- 页面缩放会改变 `getBoundingClientRect()` 的结果，但它与 `Input` 的坐标系始终同步，所以
  "先取 rect 再点中心"这条路在任何缩放下都成立。
- 坐标必须落在视口内。目标在滚动区外时先 `scrollIntoView`，`cdp.py` 已经内置这一步。

## 安全边界

调试端口 = 该浏览器配置的完全控制权（Cookie、登录态、本地存储、文件下载）。因此：

- 只绑回环地址；确需跨机时走 SSH 隧道或 `adb forward`，不要 `--remote-debugging-address=0.0.0.0`。
- 用完即关：清掉环境变量、关掉专用实例。不要把开着的调试端口留成常态。
- 不要用调试端口读取或导出凭据、Cookie、令牌；需要判断登录态就读页面上可见的状态文本。
