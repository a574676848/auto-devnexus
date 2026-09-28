---
name: image-generation
description: 使用独立脚本调用配置文件中声明的图像模型生成或编辑图片；适用于 gpt-image-2、z-image-turbo 等 OpenAI-compatible 或 DashScope 图像端点。
metadata:
  short-description: 独立图像生成与编辑
---

# 独立图像生成

默认读取当前 skill 目录内的 `config.toml`，并加载同目录 `.env`。需要其他配置时设置 `IMAGE_GENERATION_CONFIG` 或传 `--config`。配置必须包含匹配的 `[[models]]` 与 `[[providers]]`，密钥使用 `api_key_env` 指向环境变量。

先用 `--validate-config` 检查模型与 provider 关联，再用 `--dry-run` 检查请求体。需要验证另一份配置时显式传 `--config`。

```powershell
python scripts/image_generation.py --model gpt-image-2 --validate-config
python scripts/image_generation.py --model z-image-turbo --validate-config
python scripts/image_generation.py --model gpt-image-2 --prompt "一张清晰的城市夜景" --dry-run
```

`--model` 必须是 `[[models]]` 的 `name` 或 `id`。正常运行需要对应 provider 的 `api_key` 或 `api_key_env` 环境变量；输出目录默认是当前运行目录下的 `images`。

```powershell
python scripts/image_generation.py --model gpt-image-2 --prompt "一张极简风格的山水海报"
python scripts/image_generation.py --model z-image-turbo --prompt "把背景改成黄昏" --edit-image .\input.png
```

脚本只使用 Python 标准库，支持 `data:`、裸 Base64 和图片 URL 响应，并将图片保存为 PNG/JPEG/WebP 扩展名。远端 URL 默认下载到输出目录；使用 `--no-download` 可只返回 URL。
