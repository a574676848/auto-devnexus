# 疑难场景与排障

常规四步走不通时读本文件。每条都给出"为什么"和"怎么办"，因为机制清楚了才不会换个场景再翻车。

## 目录

- [点击没反应](#点击没反应)
- [输入框写了没生效](#输入框写了没生效)
- [选择器命中不到元素](#选择器命中不到元素)
- [元素在 iframe 里](#元素在-iframe-里)
- [脚本挂死不返回](#脚本挂死不返回)
- [需要用户手势的能力](#需要用户手势的能力)
- [文件上传与下载](#文件上传与下载)
- [多窗口与弹窗](#多窗口与弹窗)
- [滚动、滚轮与拖拽](#滚动滚轮与拖拽)
- [抓控制台与网络](#抓控制台与网络)
- [移动端与触摸](#移动端与触摸)
- [环境模拟](#环境模拟)
- [卡死排查顺序](#卡死排查顺序)
- [没有 Python 时的逃生通道](#没有-python-时的逃生通道)

## 点击没反应

按这个顺序查，前两步能解决绝大多数情况：

1. **先确认点到了谁。** `cdp.py click` 的 `OK:` payload 里有 `tag`（实际命中的元素）与
   `hit`（同一坐标上压在最上面的元素）。对不上就是定位问题。
2. **看是不是被遮住了。** 命中的坐标上有别的节点压着，脚本会返回 `ERR:occluded` 并给出遮住它的元素。
   正确做法是先把遮挡处理掉——关掉弹窗、切到正确的面板、等遮罩淡出——**而不是加 `-Force`**。
   `-Force` 只会把事件派发给遮罩，然后你会花时间怀疑按钮的代码。
3. **元素是不是被禁用或还没就绪。** 先 `wait -s "button.primary:not([disabled])"` 再点。
   给按钮派发事件不会绕过 `disabled`，这是好事。
4. **框架依赖 hover 或 pointer 序列。** 只用 `element.click()` 会跳过 `pointerdown`、`mouseover`、
   焦点转移。`cdp.py` 派发的是完整的
   `mouseMoved → mousePressed(buttons=1) → mouseReleased(buttons=0) → mouseMoved(buttons=0)` 序列，
   覆盖到这条链。
5. **点两次不生效，点第三次生效** 通常意味着中间有过一次重渲染把节点换掉了。这种情况下
   每次动作前重新定位（脚本每次调用都重新查询），不要在两次动作之间复用手里的坐标。
6. **虚拟列表 / 无限滚动**：目标还没被渲染出来，`no-match` 是正常的。先滚到它附近再找。

## 输入框写了没生效

**这是 CDP 里最容易"看起来成功但实际失败"的地方。** 直接给 `node.value` 赋值对受控组件完全无效：
页面的回显不变、框架的 state 不变、提交上去的是旧值，而你的脚本却返回了成功。

真机实测（同一页面，同一输入框，输入"你好 hello"）：

| 手法 | 真实 `input` 事件 | 页面回显 | JS value setter 被调用 |
|---|---|---|---|
| `Input.insertText` | 触发 | 已更新 | 否（走浏览器内部编辑管线） |
| `node.value = '...'` | 不触发 | **未更新** | 是 |

所以 `cdp.py type` 用的是 `Input.insertText`，并且在写入后**回读**输入框的值作为证据。
`OK:` payload 里的 `value` 字段就是回读结果；它和你要写的内容不一致，就说明页面改写了输入
（格式化、截断、掩码），此时应据实核对而不是重试。

补充要点：

- **先聚焦再输入**。`insertText` 打进的是"当前有焦点的编辑区"。脚本先派发真实点击来转移焦点，
  比 `element.focus()` 更接近真实用户，也能触发宿主自己的焦点逻辑。
- **清空重填**用 `-Clear`：它先选中全部内容再 `insertText`，落成一次真实的替换编辑。
- **`contenteditable` 富文本**：`insertText` 可用，但它不产生段落结构；需要换行就单独派发
  `Input.dispatchKeyEvent` 的 Enter。
- **输入法/组合输入**：`insertText` 走的是"提交文本"路径，不模拟 IME 组合过程。依赖
  `compositionstart/compositionend` 的应用可能表现不同，遇到时改用逐字符 `dispatchKeyEvent`。
- **数值型输入框**：`type="number"` 对非数字字符会静默丢弃，回读值能立刻发现。

## 选择器命中不到元素

1. **Shadow DOM**。`document.querySelector` 不进影子树。`cdp.py` 的定位器在直接查询为空时会
   自动下潜到各层 `shadowRoot`（`OK:` payload 里 `deep: true` 表示走了这条路）。
   但 `-e/--expression` 里的 `document.querySelector` **不会**自动下潜，要自己写：
   `document.querySelector('#host').shadowRoot.querySelector('.inner')`。
   嵌套影子树就逐层 `.shadowRoot`；不知道路径时用 `DOM.getDocument {pierce:true}` 拿整棵树。
2. **`display:none` 的重复项**。同一份 UI 常有隐藏副本（响应式分支、模板缓存）。
   定位器会优先在**可见**元素里挑（payload 的 `total` 与 `visible` 会告诉你各有几个）；
   真正想要隐藏那个时才用 `--index` 配合原始顺序。
3. **同类多元素**。用 `--index` 选第几个，或用 `--text` 按可见文本过滤。
4. **属性选择器里的引号**。选择器要经过一层 shell 才到脚本，两层引号规则不同：
   POSIX shell 里外层用单引号最安全 —— `-s 'button[title="提交"]'`；
   PowerShell 里同理，外层单引号、内层双引号。
   选择器里同时含单双引号时，别硬拼，改用 `-E/--expression-file` 把整段 JS 落成文件再传。
5. **动态类名**（CSS Modules、styled-components）会随构建变化，别把它们写进选择器。
   优先用 `id`、`data-*`、`aria-label`、可见文本。

## 元素在 iframe 里

`Runtime.evaluate` 默认在**主框架**执行，主框架里看不到跨源 iframe 的 DOM。三条路：

1. **同源 iframe**：直接在表达式里穿进去
   `document.querySelector('iframe').contentDocument.querySelector('.x')`。
   跨源会抛 `SecurityError`。
2. **把 iframe 当作独立目标连**（最省事）：
   `cdp.py targets --target-type iframe` 拿到它的 id，然后
   `cdp.py eval --target-id <id> -e "..."`。
3. **用执行上下文**：`Page.getFrameTree` 找到 frameId，`Page.createIsolatedWorld` 拿到
   `executionContextId`，再 `Runtime.evaluate {contextId}`。需要精确控制上下文时用这条。

`type=iframe` 的目标默认是 **out-of-process iframe**（跨源）才单独列出；同源 iframe 不会。
所以"看不到 iframe 目标"往往意味着它就是同源，走第 1 条。

## 脚本挂死不返回

按可能性排序：

1. **页面弹了原生对话框**（`alert` / `confirm` / `prompt` / `beforeunload`）。渲染进程被同步阻塞，
   `Runtime.evaluate` 会一直等下去。这是头号原因。
   处理：连上后先 `Page.enable` 并监听 `Page.javascriptDialogOpening`，收到就
   `Page.handleJavaScriptDialog {accept: true}`。已有对话框时也可以直接发一次
   `Page.handleJavaScriptDialog` 把它关掉。
2. **`awaitPromise` 等了一个永不 settle 的 Promise**。给 `Runtime.evaluate` 带 `timeout`，
   或把等待改写成有截止时间的轮询（`cdp.py wait` 就是这么做的）。
3. **目标已经销毁**（页面导航走了、窗口关了）。WebSocket 会关闭或不再回执；
   重新 `targets` 确认目标是否还在，导航后不要复用旧连接。
4. **网络请求卡住导致 `readyState` 不到 complete**。`cdp.py nav` 会报
   `ERR:nav-timeout`；改用 `wait -e "!!document.querySelector('.app-root')"` 等具体标志。
5. **调试端口被防火墙或安全软件拦下**（长时间无响应而非立刻失败）。

排查手法：把长表达式拆成几个短表达式逐步定位，或先 `eval -e "1+1"` 确认通道本身通畅。

## 需要用户手势的能力

以下 API 在"没有用户激活"时会**静默失败或抛错**，必须用 `--user-gesture`：

- `navigator.clipboard.readText()` / `writeText()`
- `window.open()`（否则被弹窗拦截器拦掉）
- `element.requestFullscreen()`
- `input.showPicker()`（日期选择器等）
- 部分自动播放与权限请求

验证手法：`eval -e "navigator.userActivation.isActive"` 在加与不加 `--user-gesture`
时分别返回 `false` 与 `true`。

剪贴板还额外需要权限。无头/全新配置下用
`Browser.grantPermissions {origin: "...", permissions: ["clipboardReadWrite"]}` 显式授权。
只是想读页面上被选中的文本时，`window.getSelection().toString()` 更省事，也不需要任何权限。

## 文件上传与下载

- **上传**：不要去找"选择文件"按钮——那会弹系统对话框，CDP 管不到它。正确做法是直接给
  `<input type="file">` 塞文件：
  `DOM.getDocument` → `DOM.querySelector` 拿 `nodeId` → `DOM.setFileInputFiles {files: [...], nodeId}`。
  找不到 input 时先点一下触发按钮让框架把 input 挂上去。
- **下载**：连上后先设 `Browser.setDownloadBehavior`
  `{behavior: "allow", downloadPath: "<dir>", eventsEnabled: true}`，再触发下载，
  监听 `Browser.downloadProgress` 判断完成。默认行为下无头模式会直接丢弃文件。
- 下载路径与上传路径都要写成参数或环境变量，不要在脚本里写死机器位置。

## 多窗口与弹窗

- 新窗口/新标签出现后会变成 `/json` 里的**新目标**。`targets` 重新看一眼，钉住它再操作。
- 想让子目标在创建时就停下来等指令：`Target.setAutoAttach
  {autoAttach: true, waitForDebuggerOnStart: false, flatten: true}`。
- `window.open` 出来的窗口同样受弹窗拦截影响，配合 `--user-gesture`。
- **别把"当前活动窗口"当成"我要操作的目标"**。以 url/title 匹配为准。

## 滚动、滚轮与拖拽

- 首选把目标 `scrollIntoView({block:'center'})` 再点，这比模拟滚轮稳得多（`click`/`type` 已内置）。
- 需要真实滚轮事件时：`Input.dispatchMouseEvent {type:'mouseWheel', x, y, deltaX:0, deltaY:300}`。
  位置必须落在**可滚动区域**上，落在固定头部上不会滚动。
- 拖动（滑块、拖拽排序）：`Input.setInterceptDrags {enabled:true}` 之后用
  `Input.dispatchDragEvent`；普通拖动也可以用 `mousePressed` → 多次 `mouseMoved` → `mouseReleased`
  手工拼出来，中间要给出足够多的移动点，只发一个终点位置多数框架不认。
- 滚到底判断：`eval -e "JSON.stringify({top:scrollY, h:innerHeight, total:document.body.scrollHeight})"`。

## 抓控制台与网络

- **没有补发**。`Log.enable` / `Runtime.enable` / `Network.enable` 之后发生的事件才会推送。
  要抓页面初始化阶段的报错，用 `Page.addScriptToEvaluateOnNewDocument` 注入一个收集器
  （把 `console.error` 与 `window.onerror` 存进数组），然后 `Page.reload`，再读那个数组。
- 网络响应体要在请求完成且尚未被驱逐前取：`Network.getResponseBody {requestId}`。
  大响应体会被丢弃，必要时用 `Fetch.enable` 拦截并自行读取。
- 只想看请求清单时，`Network.enable` 后收集 `Network.responseReceived` 的事件数组即可，
  不需要逐个取 body。

## 移动端与触摸

- `Emulation.setDeviceMetricsOverride {width, height, deviceScaleFactor, mobile: true}` 切到移动视口。
- `Input.dispatchTouchEvent` 派发 `touchStart` / `touchMove` / `touchEnd`；
  想让鼠标事件也转成触摸事件，加 `Emulation.setEmitTouchEventsForMouse {enabled: true, configuration: "mobile"}`。
- 视口覆盖是**按目标生效**的，新开的目标不会继承，操作完记得
  `Emulation.clearDeviceMetricsOverride` 还原。

## 环境模拟

| 想验什么 | 用什么 |
|---|---|
| 响应式布局 | `Emulation.setDeviceMetricsOverride` 改宽高（`shot -Width -Height` 已封装） |
| 减弱动效 | `Emulation.setEmulatedMedia {features:[{name:"prefers-reduced-motion", value:"reduce"}]}` |
| 深色模式 | `Emulation.setEmulatedMedia {features:[{name:"prefers-color-scheme", value:"dark"}]}` |
| 时区/语言 | `Emulation.setTimezoneOverride`、`Emulation.setUserAgentOverride {acceptLanguage}` |
| 地理位置 | `Emulation.setGeolocationOverride` |
| 弱网/离线 | `Network.emulateNetworkConditions` |
| 慢机器下的表现 | `Emulation.setCPUThrottlingRate` |

页面里读回真实生效值再下结论，别只看你设了什么：
`matchMedia('(prefers-reduced-motion: reduce)').matches`、`innerWidth`、`devicePixelRatio`。

## 卡死排查顺序

遇到"说不清哪里不对"，按这个顺序缩范围，每一步都要留下原始回执：

1. `info` —— 端点活着吗？协议版本是多少？
2. `targets` —— 目标在吗？是不是有多个？我钉对了吗？
3. `eval -e "1+1"` —— 通道本身通不通？
4. `eval -e "location.href"` —— 连上的是不是我想要的那个页面？
5. `eval -e "document.readyState"` —— 页面加载完了吗？
6. `eval -e "document.querySelectorAll('*').length"` —— DOM 有内容吗（还是白屏/崩溃）？
7. 再回到具体业务表达式，逐个字段试。

结论强度不要超过证据强度：只跑通第 3 步就宣称"界面正常"是不成立的，
`shot` 出来的截图与关键字段的回读值才是能给人看的证据。

## 没有 Python 时的逃生通道

`cdp.py` 只要求一个 Python 3.8+ 解释器。macOS 与绝大多数 Linux 发行版自带 `python3`，
Windows 上可能需要先装（`winget install Python.Python.3` 或从应用商店装）。
先确认：

```bash
python3 --version    # macOS / Linux
```

```powershell
python --version     # Windows；没有就试 py -3 --version
```

实在装不上 Python，可以用 Node 22+ 写一次性客户端——它自带全局 `WebSocket` 与 `fetch`，
零依赖，协议层完全一致：

```js
// node cdp-once.mjs
const port = 9444;
const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
const page = list.find((t) => t.type === 'page');
if (!page) throw new Error('no page target');

const ws = new WebSocket(page.webSocketDebuggerUrl);
const pending = new Map();
let seq = 0;
ws.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
});
await new Promise((r) => ws.addEventListener('open', r, { once: true }));

const call = (method, params = {}) => new Promise((resolve) => {
  const id = ++seq;
  pending.set(id, resolve);
  ws.send(JSON.stringify({ id, method, params }));
});

const r = await call('Runtime.evaluate', {
  expression: 'document.title', returnByValue: true, awaitPromise: true,
});
console.log(r.result.result.value);
ws.close();
```

注意这仍然只是"能跑通"的替代品：真实指针序列、命中测试、遮挡判定、目标歧义拒绝、页内轮询
这些判断力都写在 `cdp.py` 里，换到 Node 就得自己重做一遍。所以把它当逃生通道，不要当默认路径。

如果你所处的宿主有 shell 限制（例如只读沙箱），注意那种限制通常针对特定语言运行时；
`cdp.py` 是普通 Python 程序，不受 PowerShell 语言模式一类约束影响。
