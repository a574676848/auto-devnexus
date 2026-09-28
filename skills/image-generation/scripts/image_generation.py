#!/usr/bin/env python3
"""独立的 OpenAI-compatible / DashScope 图像生成客户端。"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_ROOT / "config.toml"
DEFAULT_OUTPUT_DIR = Path.cwd() / "images"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_COUNT = 1
DEFAULT_PROTOCOL = "openai"
OPENAI_PROTOCOLS = {"openai", "openai-chatcompletions"}
DASHSCOPE_PROTOCOL = "dashscope"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
OPENAI_GENERATIONS_PATH = "images/generations"
OPENAI_EDITS_PATH = "images/edits"
DASHSCOPE_IMAGE_PATH = "services/aigc/multimodal-generation/generation"
DATA_URL_PREFIX = "data:"
HTTP_SCHEMES = ("http://", "https://")


class ImageGenerationError(RuntimeError):
    """可向命令行用户展示的生图错误。"""


def load_config(path: Path) -> dict[str, Any]:
    load_dotenv(path.parent / ".env")
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except FileNotFoundError as exc:
        raise ImageGenerationError(f"配置文件不存在：{path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ImageGenerationError(f"配置文件 TOML 无效：{exc}") from exc


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(name.strip(), value)


def resolve_model(config: dict[str, Any], requested: str) -> tuple[dict[str, Any], dict[str, Any]]:
    model = next(
        (item for item in config.get("models", []) if item.get("name") == requested or item.get("id") == requested),
        None,
    )
    if model is None:
        raise ImageGenerationError(f"未找到模型：{requested}")
    provider_name = str(model.get("provider", "")).strip()
    provider = next(
        (item for item in config.get("providers", []) if item.get("name") == provider_name),
        None,
    )
    if provider is None:
        raise ImageGenerationError(f"模型 {requested} 引用的 provider 不存在：{provider_name}")
    if provider.get("enabled", True) is False:
        raise ImageGenerationError(f"provider 已禁用：{provider_name}")
    return model, provider


def provider_details(provider: dict[str, Any]) -> tuple[str, str, str | None]:
    protocol = str(provider.get("protocol") or DEFAULT_PROTOCOL).strip()
    if protocol not in OPENAI_PROTOCOLS and protocol != DASHSCOPE_PROTOCOL:
        raise ImageGenerationError(f"图像 provider 协议不受支持：{protocol}")
    base_url = str(provider.get("base_url") or "").strip().rstrip("/")
    if not base_url and protocol == DASHSCOPE_PROTOCOL:
        base_url = DASHSCOPE_BASE_URL
    if not base_url:
        raise ImageGenerationError("图像 provider 未配置 base_url")
    api_key = str(provider.get("api_key") or "").strip() or None
    if api_key is None:
        env_name = str(provider.get("api_key_env") or "").strip()
        api_key = os.environ.get(env_name, "").strip() or None
    return protocol, base_url, api_key


def read_image_reference(path: Path) -> str:
    if not path.is_file():
        raise ImageGenerationError(f"参考图片不存在：{path}")
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise ImageGenerationError(f"参考图片格式不受支持：{path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_request(model: dict[str, Any], provider: dict[str, Any], prompt: str, size: str | None,
                  quality: str | None, count: int, references: list[str]) -> tuple[str, dict[str, Any], str, str | None]:
    if not prompt.strip():
        raise ImageGenerationError("prompt 不能为空")
    if count < 1:
        raise ImageGenerationError("count 必须为正整数")
    protocol, base_url, api_key = provider_details(provider)
    model_id = str(model.get("id") or model.get("name") or "").strip()
    if not model_id:
        raise ImageGenerationError("模型缺少 id/name")
    if protocol in OPENAI_PROTOCOLS:
        path = OPENAI_EDITS_PATH if references else OPENAI_GENERATIONS_PATH
        body: dict[str, Any] = {"model": model_id, "prompt": prompt.strip(), "response_format": "b64_json", "n": count}
        if size:
            body["size"] = size.strip()
        if quality:
            body["quality"] = quality.strip()
        if references:
            body["images"] = [{"image_url": value} for value in references]
    else:
        content = [{"image": value} for value in references] + [{"text": prompt.strip()}]
        body = {"model": model_id, "input": {"messages": [{"role": "user", "content": content}]},
                "parameters": {"n": count, "watermark": False}}
        if size:
            body["parameters"]["size"] = size.strip().replace("x", "*")
        path = DASHSCOPE_IMAGE_PATH
    return f"{base_url}/{path}", body, protocol, api_key


def send_request(url: str, body: dict[str, Any], api_key: str, timeout: int) -> Any:
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ImageGenerationError(f"图像 provider 返回 HTTP {exc.code}：{detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ImageGenerationError(f"图像请求失败：{exc}") from exc


def response_items(value: Any) -> Iterable[tuple[str | None, str | None]]:
    if not isinstance(value, dict):
        return
    data = value.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item.get("b64_json"), item.get("url")
    output = value.get("output")
    if not isinstance(output, dict):
        return
    results = output.get("results")
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict):
                image = item.get("image")
                yield item.get("b64_json") or (image if isinstance(image, str) and not image.startswith(HTTP_SCHEMES) else None), item.get("url") or (image if isinstance(image, str) and image.startswith(HTTP_SCHEMES) else None)
    choices = output.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            content = choice.get("message", {}).get("content", []) if isinstance(choice, dict) else []
            for part in content:
                if isinstance(part, dict):
                    image = part.get("image")
                    yield part.get("b64_json") or (image if isinstance(image, str) and not image.startswith(HTTP_SCHEMES) else None), part.get("url") or (image if isinstance(image, str) and image.startswith(HTTP_SCHEMES) else None)


def save_item(value: str, output_dir: Path, index: int, download_url: bool) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    if value.startswith(DATA_URL_PREFIX):
        header, encoded = value.split(",", 1)
        extension = mimetypes.guess_extension(header[5:].split(";", 1)[0]) or ".png"
        content = base64.b64decode(encoded)
    elif value.startswith(HTTP_SCHEMES):
        if not download_url:
            return value
        with urllib.request.urlopen(value, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            content = response.read()
        extension = Path(urllib.parse.urlsplit(value).path).suffix or ".png"
    else:
        extension, content = ".png", base64.b64decode(value)
    path = output_dir / f"image-{index:02d}{extension}"
    path.write_bytes(content)
    return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="独立图像生成与编辑客户端")
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("IMAGE_GENERATION_CONFIG", DEFAULT_CONFIG)))
    parser.add_argument("--model", required=True, help="模型 name 或 id")
    parser.add_argument("--prompt", default="", help="生成或编辑提示词")
    parser.add_argument("--size")
    parser.add_argument("--quality")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--edit-image", action="append", type=Path, default=[])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--validate-config", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
        model, provider = resolve_model(config, args.model)
        references = [read_image_reference(path) for path in args.edit_image]
        url, body, protocol, api_key = build_request(model, provider, args.prompt or "配置验证", args.size, args.quality, args.count, references)
        summary = {"model": model.get("id"), "provider": provider.get("name"), "protocol": protocol, "url": url}
        if args.validate_config:
            print(json.dumps({"valid": True, **summary}, ensure_ascii=False, indent=2))
            return 0
        if args.dry_run:
            print(json.dumps({"valid": True, **summary, "body": body, "api_key_configured": api_key is not None}, ensure_ascii=False, indent=2))
            return 0
        if api_key is None:
            raise ImageGenerationError("未配置 API key 或 api_key_env")
        response = send_request(url, body, api_key, args.timeout)
        saved = [save_item(encoded or remote_url, args.output_dir, index, not args.no_download)
                 for index, (encoded, remote_url) in enumerate(response_items(response), 1) if encoded or remote_url]
        if not saved:
            raise ImageGenerationError("图像响应中没有可保存的图片")
        print(json.dumps({"completed": True, **summary, "images": saved}, ensure_ascii=False, indent=2))
        return 0
    except ImageGenerationError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
