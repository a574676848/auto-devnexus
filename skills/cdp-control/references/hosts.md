# 各宿主怎么开出调试端口

一条铁律贯穿全部宿主：**调试参数必须在宿主进程启动之前生效**。
进程已经在跑，再去设环境变量、改命令行，都不会有任何效果，只能重启它。

## 目录

- [先确认引擎是 Chromium](#先确认引擎是-chromium)
- [WebView2（Windows：Tauri 2 / WinUI / WPF / WinForms）](#webview2windows-tauri-2--winui--wpf--winforms)
- [Chrome / Edge / Chromium（三平台）](#chrome--edge--chromium三平台)
- [无头 Chromium / CI](#无头-chromium--ci)
- [Electron（含 VS Code 类应用）](#electron含-vs-code-类应用)
- [拿到端口的三条路](#拿到端口的三条路)
- [远程与移动端](#远程与移动端)

## 先确认引擎是 Chromium

CDP 是 Chromium 的协议。**引擎不是 Chromium 的宿主，无论怎么配都开不出 CDP 端口。**
跨平台时这一点最容易翻车，因为同一个框架在不同平台上跑的是不同引擎：

| 宿主 | Windows | macOS | Linux |
|---|---|---|---|
| Tauri 2 | WebView2（Chromium）→ **CDP 可用** | WKWebView（WebKit）→ **无 CDP** | WebKitGTK → **无 CDP** |
| Electron | Chromium → **CDP 可用** | Chromium → **CDP 可用** | Chromium → **CDP 可用** |
| Chrome / Edge / Brave | Chromium → **CDP 可用** | 同左 | 同左 |
| 系统 Safari | — | WebKit → **无 CDP** | — |

所以在 macOS 上想验证一个 Tauri 应用，CDP 这条路是走不通的，得换手段（把同一份前端产物
在 Chromium 里跑起来验证，见 SKILL.md 的"浏览器等价验证"思路）。先花十秒确认引擎，
比配半天端口最后发现协议根本不存在要划算得多。

## 判定一个现成的桌面应用能不能走 CDP

三步，全部非侵入式，**不必关掉用户正在用的应用**：

1. **进程架构**。看子进程的命令行有没有 `--type=` 参数。Chromium 系会出现
   `renderer` / `gpu-process` / `utility` 这几类；原生应用只有自己的业务子进程
   （名字通常带自家前缀）。
2. **已加载模块**（最权威）。看目标进程实际加载了哪些库：
   `libcef.dll` + `chrome_elf.dll` → CEF；配合 `.asar` 与静态链接 → Electron；
   只有自研 IPC 壳（如 `mmmojo_*.dll`）→ 界面不是 Chromium。
3. **磁盘指纹**。安装目录里有没有 `locales/`、`*.pak`、`icudtl.dat`、`snapshot_blob.bin`、`*.asar`。

判定之后要记住：**只有 Chromium 系才可能开 CDP**；而 CEF 宿主**默认关闭远程调试**，
必须宿主自己开了 `remote_debugging_port` 才会认 `--remote-debugging-port`。
Electron 宿主则默认认这个参数（除非它主动过滤了 argv）。

### 三个实测样本

| 应用 | 判定依据 | 结论 |
|---|---|---|
| 飞书桌面端 | MAIN + 4 renderer + gpu-process + 3 utility；目录含 `admin.asar`/`calendar.asar`/`contacts.asar`、`locales/`、`icudtl.dat`、`resources.pak` | Electron，Chromium 内核，启动参数大概率生效 |
| 钉钉桌面端 | MAIN + 3 renderer + gpu-process + 2 utility；已加载 `libcef.dll`、`chrome_elf.dll`、`runtime_v8.dll`；目录含 `locales/`、`snapshot_blob.bin` | CEF，Chromium 内核，但远程调试默认关闭，取决于宿主是否开放 |
| 微信 4.x | MAIN×2 + wxocr/wxplayer/wxpublic/wxutility/xplayer；仅 `mmmojo_*.dll`；无 `.pak`/`locales/`/`.asar`，无 renderer 进程 | 主界面非 Chromium，**CDP 无解**，不要在这上面花时间 |

### 正在运行的应用，参数一定进不去

单实例锁会把新进程的命令行参数**静默丢弃**：进程数不变、端口不开、应用照常显示原窗口。
实测飞书与钉钉都是这个行为，而且**飞书连 `--user-data-dir` 换独立 profile 也绕不过**
（它的锁是全局的，与数据目录无关）。

所以：

- 想拿到端口只有一条路：**完整退出应用，再用参数重启**。这会打断用户正在使用的应用，
  企业 SSO 环境下还可能要求重新登录。动手前先取得用户明确同意，并给出可回退的方案。
- **先问"有没有更正规的接口"再考虑驱动界面。** 办公类桌面端通常自带官方数据面
  （如飞书有 lark-cli，钉钉有 dws 系列命令），那些比外挂调试端口稳定得多。
  驱动界面是最后手段，不是第一选择。
- 部分宿主自带"开发者工具"入口（多见于其小程序/内置浏览器容器），那比从外部开调试端口正规。

## WebView2（Windows：Tauri 2 / WinUI / WPF / WinForms）

WebView2 内核就是 Edge，所以 `/json`、协议版本与 Edge 完全一致。这是 Windows 专属运行时。

**从外部启动时**用环境变量（进程级，对该进程创建的所有 WebView2 生效）：

```powershell
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9333'
# 这一行之后再启动宿主
```

**从代码里启动时**走 `CoreWebView2EnvironmentOptions.AdditionalBrowserArguments`，效果相同。

踩坑点：

- 环境变量对**已经存在**的 WebView2 运行时无效。宿主必须由你这次启动的进程创建。
- 同一进程里的多个 WebView2 共用这一个端点，目标列表里会出现多个 `page`——正好是必须钉目标
  （`--url-match` / `--target-id`）的典型场景。
- 有些宿主会把环境变量过滤掉再传给子进程。如果 `info` 报 `ERR:no-endpoint`，先确认变量确实在
  当前 shell 里，再确认宿主是被这个 shell 拉起来的。
- 验证结束后**清掉这个变量**，不要把调试端口带进日常使用。

## Chrome / Edge / Chromium（三平台）

不要写死安装路径，先用系统自己的查找能力定位可执行文件：

```bash
# macOS / Linux
CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser \
  || command -v microsoft-edge || echo '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')"
"$CHROME" --remote-debugging-port=9222 --user-data-dir="$(mktemp -d)" --no-first-run --no-default-browser-check
```

```powershell
# Windows
$chrome = (Get-Command chrome.exe -ErrorAction SilentlyContinue).Source
if (-not $chrome) { $chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe" }
$profile = Join-Path $env:TEMP ([guid]::NewGuid().ToString('N'))
& $chrome --remote-debugging-port=9222 --user-data-dir="$profile" --no-first-run --no-default-browser-check
```

**必须带 `--user-data-dir` 指向一个专用目录。** 如果新进程发现默认配置目录已被现有实例占用，
它会把这个进程直接转交给现有实例，调试参数被**静默丢弃**——端口不开，也不报错。这是
"命令行明明写了 `--remote-debugging-port` 却连不上"的头号原因。新版 Chrome（136 起）更进一步：
直接拒绝对默认配置目录开启远程调试。

其他常用参数：

| 参数 | 用途 |
|---|---|
| `--headless=new` | 无窗口运行，行为和真实窗口基本一致 |
| `--remote-allow-origins=*` | 只有"从浏览器页面里的 JS 去连 CDP"时才需要 |
| `--remote-debugging-port=0` | 让系统分配随机端口，端口号写进 `<user-data-dir>/DevToolsActivePort` |
| `--window-size=1280,800` | 固定初始视口，便于截图比对 |
| `--no-sandbox` | **仅在容器/以 root 运行的 Linux** 上才需要；不要在日常桌面环境加 |
| `--disable-gpu` | 无头环境下避免合成相关的不稳定 |

`DevToolsActivePort` 文件的内容是两行：第一行端口号，第二行是 browser 级 WebSocket 路径。
并行跑多个实例时用 `--remote-debugging-port=0` + 读这个文件，比手工分配端口稳。

Linux 上启动即退出、报缺 `libnss3` / `libatk` / `libgbm` 一类共享库，是精简镜像缺依赖，
按报错补齐即可，跟 CDP 本身无关。

## 无头 Chromium / CI

```bash
# macOS / Linux
"$CHROME" --headless=new --disable-gpu --no-first-run \
  --user-data-dir="$(mktemp -d)" --remote-debugging-port=0 \
  --window-size=1280,800 "file:///path/to/page.html"
# 端口从 <user-data-dir>/DevToolsActivePort 第一行读
```

```powershell
# Windows
& $chrome --headless=new --disable-gpu --no-first-run `
  --user-data-dir="$profile" --remote-debugging-port=0 `
  --window-size=1280,800 "file:///C:/path/to/page.html"
```

无头模式下 `Page.captureScreenshot`、`Emulation.*`、`Input.*` 全部可用，是回归与取证最稳的环境；
但它没有真实 GPU 合成与窗口管理，**窗口级行为（最小化、置顶、多显示器）必须在真窗口里另验**。

## Electron（含 VS Code 类应用）

Electron 的渲染进程在三个平台上都是 Chromium，参数同名：

```bash
./your-app --remote-debugging-port=9222
```

踩坑点：

- 打包后的应用常自带参数解析器，会丢掉不认识的开关。若端口没开，改在应用代码里
  `app.commandLine.appendSwitch('remote-debugging-port', '9222')`。
- `--inspect` / `--inspect-brk` 开的是 **Node 主进程**调试端口（默认 9229），和渲染进程的
  `--remote-debugging-port` 是两套东西，`/json` 不会出现在 `--inspect` 端口上（除非应用同时开了）。
- macOS 上从 Finder 双击启动的应用拿不到你 shell 里的参数，必须从命令行启动，或把开关写进代码。

## 拿到端口的三条路

1. **你自己定的**：启动时显式给了 `--remote-debugging-port=9222`，照用。
2. **系统分配的**：启动时给了 `0`，读 `<user-data-dir>/DevToolsActivePort` 第一行。
3. **不确定**：让 `cdp.py` 自动探测（省略 `--port`），它会依次试
   `9333`、`9222`、`9229`、`9444`、`9223`、`8315`。

探测到多个端口同时活着时，**脚本不会替你合并结果**——每个 `--port` 是一个独立端点，分别查询。
同一台机器上同时跑着多个 Chromium 系程序是常态（桌面应用 + 浏览器 + 调试实例），
所以"探测到端口"只说明有人在那儿，不说明那就是你要操作的那个。

## 远程与移动端

跨机时一律走隧道，不要把调试端口暴露到网络上：

```bash
# Android Chrome
adb forward tcp:9222 localabstract:chrome_devtools_remote

# 任意远端主机
ssh -L 9222:127.0.0.1:9222 user@host
```

隧道打通后本地 `127.0.0.1:9222` 就是那台设备/主机的调试端点，本文其余手法原样适用。
Android 上 `Input.*` 的坐标同样是该设备 WebView 的 CSS 像素，注意移动端视口尺寸与 DPR。
