# Laya 语义判定（可选增强）

CDP 定位靠 CSS 选择器与文本匹配，这条路在两种情况下会卡住：类名是构建期哈希、UI 被本地化，
以及页面上有五个长得一模一样的按钮而你要的是"提交"那个。Laya 用一次前向传播把这件事变成一道
带概率的选择题，于是你可以对结果设阈值，而不是拿到一个没有刻度的猜测。

本文件讲清楚三件事：怎么配、怎么用、**以及它在什么情况下不可信**。第三部分请务必读完再动手。

## 这是什么

[Laya](https://github.com/NandhaKishorM/laya) 是非自回归的 System-1 决策模型，以 TypeSafe Jev
`/v1/systemone` 协议提供服务。一次请求可以同时问多个问题，每题三种类型之一：

| type | 语义 | 返回 |
|---|---|---|
| `choice` | 从一组候选里选一个 | `choice` + `probabilities`（各候选归一化概率） |
| `score` | 把一个输入放到有序刻度上 | `score` + `legend`（`criteria` 数组顺序映射到 0/1/2/…） |
| `noul` | 校准的是/否强度 | `noul`（0–1） |

每题还会带 `confidence`、`answer_confidence` 与 `action.act_probability`。
`answer_confidence` 是落在获胜选项上的概率质量，通常就是你要的那个数。

CPU 后端上单次推理约 3 秒（首次预载后），所以**把多个问题放进同一次请求**，而不是连着发几次。

## 怎么配

本 Skill 不内置任何服务地址。地址与令牌一律由环境或配置文件提供，解析顺序（先命中先用）：

| 项 | 顺序 |
|---|---|
| base URL | `--laya-url` → `CDP_LAYA_BASE_URL` → `LAYA_BASE_URL` → 配置文件 |
| api key | `--laya-key` → `CDP_LAYA_API_KEY` → `LAYA_API_KEY` → 配置文件 |
| 超时秒 | `--laya-timeout` → `CDP_LAYA_TIMEOUT` → 配置文件 → 120 |

配置文件路径：`$CDP_LAYA_CONFIG`，未设则 `~/.config/cdp-control/laya.json`（三平台通用）：

```json
{
  "base_url": "http://<laya-host>:<port>",
  "api_key": "<token>",
  "timeout_seconds": 120
}
```

`api_key` 只在服务端配了令牌时才需要；留空即不带 `Authorization` 头。

### 先确认连通

```bash
python3 cdp.py laya-health
```

`OK:{"status":"ok","device":"cpu","loaded":[...],"baseUrl":"..."}` 即通。
`ERR:laya-unconfigured` 会直接把上面那张表的解析顺序与配置文件路径打给你，照着配即可。

### 代理是会咬人的那一环

`HTTP_PROXY` / `HTTPS_PROXY`，以及 TUN 模式的代理客户端（clash 一类），会把发往私网地址的请求
劫持走，症状是连不上或超时，而 `curl` 又"看起来没问题"。本 Skill 对**私网/回环主机自动绕过代理**
（`urllib` 的 `ProxyHandler({})`），公网地址仍走系统代理。判断依据是 RFC1918、回环、链路本地，
以及不带点的单标签主机名。如果你把 Laya 放在公网域名后面又希望直连，那是另一回事，需要你在
代理侧放行。

## 怎么用

### `pick`：在一组候选元素里选一个

```bash
# 只看不点（默认），拿到选择与概率
python3 cdp.py pick --url-match "app" -s "button" --intent "提交当前表单"

# 直接点中它（内部仍走真实鼠标序列，并同样做遮挡判定）
python3 cdp.py pick --url-match "app" -s "form button" --intent "提交当前表单" --click
```

回执字段：

| 字段 | 含义 |
|---|---|
| `element` | 被选中元素的可读描述（同时也是喂给模型的 criteria key） |
| `probability` | 获胜候选的概率质量 |
| `runnerUpMargin` | **获胜者与第二名的差距**，判断可信度看这个而不是上一个 |
| `probabilities` | 全部候选的概率分布，用于判断"是不是池子本身没有区分度" |
| `candidatesDescribed` / `candidatesMatched` | 描述了几何 / 命中几何（只描述可见元素） |
| `shadowFallback` / `truncated` | 是否走了 Shadow DOM 下潜 / 候选是否被 `--limit` 截断 |

`--min-margin`（默认 0.10）在领先幅度不足时直接报 `ERR:pick-low-margin` 并附上完整概率分布。
`--min-probability` 是绝对概率下限。

### `judge`：对当前页面状态问一道校准题

```bash
# 是/否：拿 0-1 的强度
python3 cdp.py judge --url-match "app" --question "表单是否已经提交成功？"

# 分档：按 --criteria 顺序映射到 0/1/2/…
python3 cdp.py judge --url-match "app" --type score \
  --question "当前页面的完成度如何？" --criteria "未开始,进行中,已完成"

# 分类：key=description
python3 cdp.py judge --url-match "app" --type choice \
  --question "当前处于哪种状态？" --criteria "idle=无进行中操作,busy=加载中,error=报错"
```

`--context-selector`（默认 `body`）决定把哪块文本当作"状态"送过去，`--max-chars` 截断，
`--with-url` 顺带带上标题与 URL。`--min-confidence` 低于阈值时报 `ERR:judge-low-confidence`。

## 什么时候**不要**用它（实测边界，先读这段）

以下都是在真实部署（CPU 后端，`typed-decisions` + `multilingual` 检查点）上测出来的数字，
不是估计。同一个输入重复调用结果**逐位相同**——它是确定性模型，所以这些数字是稳定特征，
不是随机噪声。

**1. 它对提示构造高度敏感，而领先幅度普遍很小。**
同一个"点击显示遮罩那个按钮"的意图，换一种 criteria 写法：

| criteria key 写法 | 选对 | 获胜概率 | 领先幅度 |
|---|---|---|---|
| 合成 key `0\|点击计数` | 否 | — | 0.032 |
| 描述文本直接当 key（中文状态） | 是 | 0.3556 | 0.0784 |
| 描述文本直接当 key（另一种模板） | 是 | 0.6547 | 0.5075 |
| `[n] 描述` 带序号前缀 | 否 | 0.4397 | 0.1863 |

结论：**用可读描述当 key，不要用合成 key 或序号前缀**（本 Skill 已经这么做）。但也要接受
"改几个字就换个答案"这个事实。

**2. 候选池越大越不可信。**
四选一、意图又写得含糊时，0.15 左右的领先幅度仍然可能选错；而把池子收窄到真正互相竞争的两三个，
概率会跳到 1.0。所以 `pick` 的正确用法是**先用选择器/文本把候选池收窄，再让模型在少数近义候选里排序**，
而不是拿它去扫全页按钮。

**3. 上下文里没有的证据，它答不出来。**
`judge` 只看到 `--context-selector` 的文本。问"遮罩是否打开"却只给 `body` 的可见文本，
它拿不到 `display` 这类样式事实，就会给出一个自信但没有依据的答案。
**要么把证据放进上下文，要么改用 `eval` 直接读回真实值。**

**4. 因此它绝不可以当作唯一权威。**
把 `pick` 当成"缩小范围后的排序建议"，把 `judge` 当成"给我一个可设阈值的信号"。
不论哪个，**动作之后都要按铁律复验**：`pick --click` 之后照样 `eval` 读回真实状态，
`judge` 的结论要和 `eval` 的硬读数交叉核对。两者冲突时，**以 `eval` 的真实读数为准**。

**5. 它不该出现在关键路径上。**
服务不可达、未配置、超时——都只是 `ERR:laya-*`，选择器路径完全不受影响。
没有 Laya，这个 Skill 照常工作，只是少了一个语义助手。
