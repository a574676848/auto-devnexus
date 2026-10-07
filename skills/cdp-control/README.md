# cdp-control

用 Chrome DevTools Protocol 直接驱动并取证任意 Chromium 内核界面。

它填补的空位是：**任意 Chromium 内核的、已经在跑的窗口**。Playwright 只能驱动它自己启动的浏览器，
浏览器扩展只能管标签页，而"桌面上那个已经装好的 Tauri / Electron / WebView2 应用"——只有 CDP 进得去。

再叠两条硬约束：

- **零依赖**：纯 Python 3 标准库，不需要 pip install，不需要下载浏览器驱动。整个技能可以直接 vendor 进任何仓库。
- **证据式契约**：每条命令只输出一行 `OK:` 或 `ERR:`，判定看前缀而不是退出码；动作之后回读真实状态、留截图。

## 环境要求

一个 Python 3.8+ 解释器，没有别的。

| 平台 | 用哪个命令名 |
|---|---|
| macOS / Linux | `python3` |
| Windows | `python`（没装就用 `py -3`） |

macOS 与绝大多数 Linux 发行版自带 `python3`；Windows 上可从 [python.org](https://www.python.org/downloads/)
或应用商店安装。

## 安装

把 `cdp-control/` 整个目录放进你的技能目录即可（例如 Claude Code / Codex 的 `skills/`，或本仓库的 `skills/`）。
不需要任何安装脚本，四个 `.py` 文件必须放在一起——`cdp.py` 会 import 同目录的另外三个。

## 快速上手

先给宿主开调试端口。**参数必须在宿主启动之前生效**，已经跑着的进程改环境变量没有用。

```powershell
# Windows：WebView2 / Tauri 2 桌面端
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9333'
# 然后才启动你的应用
```

```bash
# macOS / Linux：Electron 应用或 Chrome
./your-app --remote-debugging-port=9222
```

然后：

```bash
python3 scripts/cdp.py info                       # 端点活着吗（省略 --port 会自动探测常见端口）
python3 scripts/cdp.py targets                    # 有哪些窗口/标签
python3 scripts/cdp.py eval  --url-match app -e "document.title"
python3 scripts/cdp.py click --url-match app -s "button.primary" --text "提交"
python3 scripts/cdp.py type  --url-match app -s "textarea" -t "你好" --submit
python3 scripts/cdp.py wait  --url-match app -s ".result" --timeout 15000
python3 scripts/cdp.py shot  --url-match app -o ./evidence/after.png
```

## 命令一览

| 命令 | 作用 |
|---|---|
| `info` / `targets` | 端点存活、调试目标列表 |
| `eval` | 求值并打印返回值 |
| `click` | 滚动到位、命中测试、派发真实鼠标序列 |
| `type` / `key` | 真实文本输入（`Input.insertText`）、按键派发 |
| `wait` | 页内轮询直到条件成立（或消失） |
| `text` / `html` | 读元素的 innerText / outerHTML |
| `shot` | 截图落盘，支持整页与视口覆盖 |
| `nav` / `open` / `close` | 导航、新开标签页、关闭目标 |
| `pick` / `judge` / `laya-health` | 可选的语义判定，见下节 |

选择目标用 `--port`、`--url-match`、`--target-id`、`--target-type`、`--first`。
**端点上不止一个页面时必须钉住目标**：调试端点的目标顺序会随标签页开合变化，脚本在多个目标都匹配
且没有指定时会直接报 `ERR:ambiguous-target`，而不是替你猜。

退出码默认恒为 0，需要在 shell 里串联时加 `--strict-exit`。

## 可选：语义判定（Laya）

类名是构建哈希、界面被本地化、五个按钮长得一样时，可以接入
[Laya](https://github.com/NandhaKishorM/laya) 决策模型做一次带概率的选择：

```bash
python3 scripts/cdp.py laya-health                     # 先确认服务通
python3 scripts/cdp.py pick -s "form button" --intent "提交当前表单" --click
python3 scripts/cdp.py judge --question "表单是否已提交成功？"
```

地址与令牌全部由环境变量或配置文件提供，**代码里不写死任何服务地址**：

| 项 | 解析顺序（先命中先用） |
|---|---|
| base URL | `--laya-url` → `CDP_LAYA_BASE_URL` → `LAYA_BASE_URL` → 配置文件 |
| api key | `--laya-key` → `CDP_LAYA_API_KEY` → `LAYA_API_KEY` → 配置文件 |

配置文件路径为 `$CDP_LAYA_CONFIG`，未设则 `~/.config/cdp-control/laya.json`：

```json
{
  "base_url": "http://<laya-host>:<port>",
  "api_key": "<token>"
}
```

未配置时 `pick` / `judge` 会返回 `ERR:laya-unconfigured` 并打印上面这张表，其余全部命令不受影响。

> **请按实测边界使用它。** 实测发现该模型对提示构造高度敏感，候选之间的领先幅度普遍只有
> 0.03–0.19，微调写法就可能翻转答案。所以脚本把 `criteria` 的 key 设为元素的可读描述
> （实测最优），并用 `--min-margin`（默认 0.10）在领先不足时**报错而不是悄悄选错**。
> 完整数据与五条边界见 [references/laya.md](references/laya.md)。

## 平台与引擎支持

CDP 是 Chromium 的协议，**引擎不是 Chromium 的宿主无论怎么配都开不出端口**：

| 宿主 | Windows | macOS | Linux |
|---|---|---|---|
| Chrome / Edge / Brave | 支持 | 支持 | 支持 |
| Electron 应用 | 支持 | 支持 | 支持 |
| Tauri 2 | 支持（WebView2） | 不支持（WKWebView） | 不支持（WebKitGTK） |
| 系统 Safari | — | 不支持 | — |

各宿主具体的开端口方式见 [references/hosts.md](references/hosts.md)，其中也包含「怎么判断一个现成的
桌面应用到底能不能走 CDP」的三步非侵入式判定法。

## 文档

| 文件 | 内容 |
|---|---|
| [SKILL.md](SKILL.md) | Agent 调用入口：四步闭环、命令清单、铁律、故障速查 |
| [references/protocol.md](references/protocol.md) | CDP 协议速查：帧格式、参数语义、常用方法 |
| [references/hosts.md](references/hosts.md) | 各宿主开调试端口、引擎判定法、远程与移动端 |
| [references/cases.md](references/cases.md) | 疑难场景：iframe、用户手势、上传下载、多窗口、排障顺序 |
| [references/laya.md](references/laya.md) | Laya 语义判定的配置、用法与实测边界 |

## 安全提示

调试端口等价于该浏览器配置的完全控制权（Cookie、登录态、本地存储）。因此：

- 只绑回环地址；跨机时用 SSH 隧道或 `adb forward`，不要暴露到网络。
- 用完即关：清掉调试端口环境变量或关掉专用实例。
- 不要用调试端口读取或导出凭据、Cookie、令牌。

## 许可证

本技能随 [auto-devnexus](../..) 仓库一同分发，遵循仓库的许可证。

其中 `scripts/cdpws.py` 包含一份最小化的 RFC 6455 WebSocket 客户端实现，用于避免引入第三方依赖。
Laya 语义判定为可选集成，Laya 本身由其各自仓库的许可证约束。
