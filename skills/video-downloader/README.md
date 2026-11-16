# Video Downloader

把一条视频链接或本地视频，变成一份带时间戳的纯文本 `multimodal_transcript.md`：平台字幕、云端语音识别、关键帧/完整视频/片段级视觉理解全部汇总到一起，下游可以直接当普通文本消费。

它解决的是「视频内容进不了文本流水线」这件事：抖音、B 站、YouTube、小红书、视频号（实验性）以及本地文件都能走同一套 ASR + 视觉分析流程，产出统一格式的转写稿，供代码助手、知识库或其它 Skill 继续加工。

## 核心能力

| 能力 | 说明 |
|---|---|
| 视频获取 | 抖音 / B 站 / YouTube / 小红书 / 视频号 / 本地文件 |
| 平台字幕 | 优先复用平台自带字幕轨，区分人工与自动来源 |
| 云 ASR | Ark `doubao-seed-asr-2.0` → SiliconFlow `SenseVoiceSmall` → 本地 Whisper（需显式授权） |
| 视觉理解 | 关键帧 / 完整视频 / Agent 选段三种模式，走百炼 `qwen3.8-omni-flash` 原生 `video_url` |
| 时间轴对齐 | 画面观察与同期语音按毫秒对齐，输出带时间戳的 Markdown |
| 断点续跑 | ASR、选段、原生视频分析均按指纹落缓存，重跑只补失败部分 |

## 依赖

必需：

- Python 3.10+
- `ffmpeg` / `ffprobe`
- `yt-dlp`（B 站、YouTube、小红书；部分平台作为兜底）

可选：

- `ARK_API_KEY`：Ark ASR 与豆包视觉
- `BAILIAN_API_KEY`：百炼 `qwen3.8-omni-flash` 原生视频理解
- `TOKENRHYTHM_API_KEY`：`qwen3.8-flash` 视觉兜底
- `SILICONFLOW_API_KEY`：云 ASR 兜底
- Playwright：视频号首次交互授权

## 快速开始

平台链接 + 自动挑选视觉后端：

```bash
python3 scripts/download_video.py "https://www.youtube.com/watch?v=..." \
  --output-dir ./downloads \
  --asr auto \
  --vision auto \
  --vision-mode agent-clips \
  --profile knowledge
```

本地视频（只需要百炼 Key）：

```bash
python3 scripts/download_video.py "/absolute/path/demo.mp4" \
  --output-dir ./downloads \
  --local-caption "产品演示" \
  --local-author "作者名" \
  --asr none \
  --vision bailian \
  --vision-mode keyframes \
  --profile tech
```

只取平台文案与元信息：

```bash
python3 scripts/download_video.py "https://v.douyin.com/..." \
  --output-dir ./downloads \
  --metadata-only
```

常用参数：

```text
--vision auto|bailian|doubao|tokenrhythm|doubao-responses|none
--vision-mode keyframes|full-video|agent-clips
--vision-plan-only          只做本地准备，不发起云端视觉请求
--confirm-cloud-upload      非交互运行的一次性上传授权
--vision-max-clips 8
--vision-max-clip-seconds 600
--vision-concurrency 4
--force-reprocess           绕过 ASR / 选段 / 原生视频结果缓存
```

## 三种视觉模式怎么选

| 模式 | 送给云端的内容 | 优势 | 局限 |
|---|---|---|---|
| `keyframes` | 场景变化 + 固定间隔抽出的 JPEG | 最省 token | 可能漏掉动作与未采样区间 |
| `full-video` | 720p 压缩代理，按 10 分钟切块 | 覆盖全片 | 输入更贵，压缩可能损失小字 |
| `agent-clips` | 先发时间戳文本选段，再发有界 MP4 片段 | 平衡最好，推荐 | 依赖可靠的时间戳 ASR |

非交互运行时未指定 `--vision-mode` 会以退出码 2 终止，不会替用户静默选择。

## 大文件怎么进云端

百炼 omni 接受原生 `video_url`，这个技能只送两种来源：

1. 公网可直接访问的 HTTP(S) 链接（平台直链）——原样透传；
2. 不超过 10 MB 的本地片段——内联为 `data:video/mp4;base64,...`。

超过 10 MB 的本地片段不会被上传到任何第三方存储：该片段记一条 error，由 pipeline 自动回退到本地抽帧，分析照常完成，证据类型从 `native-video` 变成 `video-frame`。需要原生视频理解又超限时，自行把片段压到 10 MB 以内，或提供公网直链。

## 输出

```text
downloads/<platform>-<id>/
├── video.mp4
├── post_caption.txt
├── metadata.json
├── audio.mp3
├── transcript.txt
├── transcript.segments.jsonl
├── frames/
├── visual_notes.jsonl
├── vision_plan.json
├── vision_selection_plan.json     # Agent 模式
├── clip_selection.json            # Agent 模式
├── vision/
│   ├── full-video-proxy.mp4       # 完整视频模式
│   └── clips/*.mp4                # Agent 模式
├── timings.json
└── multimodal_transcript.md       # 最终交付
```

`multimodal_transcript.md` 是唯一的交接产物：普通文本，带时间戳，区分「画面事实」「屏幕文字」「动作」「模型推断」四类信息，推断部分明确标注需复核。

## 目录结构

```text
video-downloader/
├── SKILL.md
├── README.md
├── THIRD_PARTY_NOTICES.md
└── scripts/
    ├── download_video.py          # CLI 入口
    ├── providers/                 # 各平台抓取
    ├── vision/                    # 视觉后端、抽帧、切段、临时托管
    ├── asr.py / asr_ark.py        # 语音识别
    └── media_probe.py / subtitles.py / text_renderer.py
```

## 环境变量

| 变量 | 用途 |
|---|---|
| `ARK_API_KEY` | Ark ASR 与豆包视觉 |
| `BAILIAN_API_KEY` / `DASHSCOPE_API_KEY` | 百炼视觉 |
| `BAILIAN_BASE_URL` | 覆盖百炼兼容端点（默认标准 DashScope 端点；使用专属 workspace 端点时设置） |
| `TOKENRHYTHM_API_KEY` | TokenRhythm 视觉兜底 |
| `SILICONFLOW_API_KEY` | 云 ASR 兜底 |

密钥只放环境变量或私有配置文件，绝不写进本仓库。

## 故障排除

| 现象 | 原因与处理 |
|---|---|
| `python3` 无任何输出 | Windows 上 `python3` 可能是应用商店空壳别名，改用 `python` |
| 找不到 `ffmpeg` | winget 安装的别名在 `%LOCALAPPDATA%\Microsoft\WinGet\Links\`，先刷新 PATH |
| 抖音抓取提示需要 cookie | 抖音 SSR 已不再向未登录请求下发视频数据，改用已登录浏览器的页面直链 |
| 百炼返回 401 | 确认 Key 对应的是 `compatible-mode`；使用专属 workspace 端点时设置 `BAILIAN_BASE_URL` |
| 本地视频超 10 MB 直接回退抽帧 | 未配置 OSS 临时托管，或上传失败，检查上文凭据文件 |
| ASR 返回 `pending` / 退出码 3 | 缺少可用 ASR 后端，按提示提供 SiliconFlow Key 或显式选择本地 Whisper |

## 说明

本 Skill 的下载、ASR、抽帧与视觉编排来自 `kangarooking/kangarooking-skills`，在此基础上增加了百炼原生视频的本地大文件托管通道、Windows 部署备注与故障排查表。第三方组件许可见 `THIRD_PARTY_NOTICES.md`。

只处理你拥有、已获授权或可合法归档的素材；不绕过 DRM、付费访问与平台访问控制。
