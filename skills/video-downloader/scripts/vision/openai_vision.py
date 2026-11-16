"""OpenAI-compatible multimodal vision clients.

Three interchangeable profiles, ordered by preference in :data:`BACKEND_ORDER`:

* ``bailian``     Aliyun Bailian (DashScope compatible mode), default ``qwen3.8-omni-flash``.
* ``doubao``      Volcano Ark Agent Plan gateway (``/api/plan/v3``), default ``doubao-seed-evolving``.
* ``tokenrhythm`` TokenRhythm OpenAI-compatible relay, default ``qwen3.8-flash``.

All three accept inline ``image_url`` data URLs. None of them exposes the Ark
Responses/Files API pair that :mod:`vision.doubao` uses, so native upload-based
video analysis is unavailable here. Video items are analysed by sampling frames
locally and asking the image model about each batch, then re-basing timestamps
onto the source timeline.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import tempfile
import time
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .doubao import _data_url, _parse_notes, _parse_video_notes, _prompt, _string_list, _video_prompt


# 标准 DashScope 兼容端点；需要百炼专属 workspace 端点时用 BAILIAN_BASE_URL 覆盖。
BAILIAN_BASE_URL = os.environ.get(
    "BAILIAN_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
).rstrip("/")
DOUBAO_PLAN_BASE_URL = "https://ark.cn-beijing.volces.com/api/plan/v3"
TOKENRHYTHM_BASE_URL = "https://tokenrhythm.studio/v1"

BAILIAN_DEFAULT_MODEL = "qwen3.8-omni-flash"
DOUBAO_DEFAULT_MODEL = "doubao-seed-evolving"
TOKENRHYTHM_DEFAULT_MODEL = "qwen3.8-flash"

BACKEND_ORDER = ("bailian", "doubao", "tokenrhythm")

DEFAULT_MODELS = {
    "bailian": BAILIAN_DEFAULT_MODEL,
    "doubao": DOUBAO_DEFAULT_MODEL,
    "tokenrhythm": TOKENRHYTHM_DEFAULT_MODEL,
}

DEFAULT_BASE_URLS = {
    "bailian": BAILIAN_BASE_URL,
    "doubao": DOUBAO_PLAN_BASE_URL,
    "tokenrhythm": TOKENRHYTHM_BASE_URL,
}

KEY_ENV_VARS = {
    "bailian": ("BAILIAN_API_KEY", "DASHSCOPE_API_KEY"),
    "doubao": ("ARK_API_KEY",),
    "tokenrhythm": ("TOKENRHYTHM_API_KEY",),
}

MAX_IMAGES_PER_REQUEST = 20
MAX_IMAGE_BYTES = 10_000_000
MAX_INLINE_VIDEO_BYTES = 10_000_000
NATIVE_VIDEO_BACKENDS = ("bailian",)


def backend_key(backend: str) -> str | None:
    """Return the credential for *backend* from env, then from its CLI config file."""
    for name in KEY_ENV_VARS.get(backend, ()):
        value = os.environ.get(name)
        if value:
            return value
    if backend == "bailian":
        config = Path.home() / ".bailian" / "config.json"
        if config.is_file():
            try:
                payload = json.loads(config.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            value = str(payload.get("api_key") or "").strip()
            if value:
                return value
    if backend == "doubao":
        for path in sorted((Path.home() / ".arkcli" / "identities").glob("*/apikey.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            value = str(payload.get("api_key") or "").strip()
            if value:
                return value
    return None


def backend_available(backend: str) -> bool:
    return backend_key(backend) is not None


def first_available_backend() -> str:
    for backend in BACKEND_ORDER:
        if backend_available(backend):
            return backend
    return BACKEND_ORDER[0]


def resolve_model(backend: str, model: str | None) -> str:
    if model and model not in {"auto", ""}:
        return model
    return DEFAULT_MODELS[backend]


def analyze_frames(
    frames: list[dict],
    *,
    model: str | None = None,
    profile: str = "knowledge",
    custom_prompt: str | None = None,
    batch_size: int = 4,
    timeout: int = 180,
    backend: str = "bailian",
) -> tuple[list[dict], list[dict]]:
    """Send keyframes to one OpenAI-compatible chat/completions endpoint."""
    api_key = backend_key(backend)
    if not api_key:
        raise RuntimeError(
            f"No credential for vision backend '{backend}' "
            f"(set {' or '.join(KEY_ENV_VARS[backend])})."
        )
    if batch_size <= 0 or batch_size > MAX_IMAGES_PER_REQUEST:
        raise RuntimeError(f"Vision batch size must be between 1 and {MAX_IMAGES_PER_REQUEST}.")
    resolved_model = resolve_model(backend, model)
    notes: list[dict] = []
    errors: list[dict] = []
    for offset in range(0, len(frames), batch_size):
        batch = frames[offset : offset + batch_size]
        try:
            for frame in batch:
                path = Path(frame["path"])
                if path.stat().st_size > MAX_IMAGE_BYTES:
                    raise RuntimeError(f"Image exceeds the 10 MB limit: {path.name}")
            content: list[dict] = [{"type": "text", "text": _prompt(batch, profile, custom_prompt)}]
            content.extend(
                {"type": "image_url", "image_url": {"url": _data_url(Path(frame["path"]))}}
                for frame in batch
            )
            text = _chat_text(
                backend=backend,
                api_key=api_key,
                model=resolved_model,
                content=content,
                timeout=timeout,
                max_tokens=8192,
            )
            parsed = _parse_notes(
                {"status": "completed", "output_text": text},
                batch,
                model=resolved_model,
                profile=profile,
            )
            for note in parsed:
                note["backend"] = backend
            notes.extend(parsed)
        except (RuntimeError, OSError, ValueError, TypeError) as exc:
            errors.append({"frame_ids": [frame.get("id") for frame in batch], "error": str(exc)})
    return notes, errors


def request_text_json(
    prompt: str,
    *,
    model: str | None = None,
    timeout: int = 600,
    thinking: str = "disabled",
    backend: str = "bailian",
) -> dict:
    api_key = backend_key(backend)
    if not api_key:
        raise RuntimeError(f"No credential for vision backend '{backend}'.")
    resolved_model = resolve_model(backend, model)
    text = _chat_text(
        backend=backend,
        api_key=api_key,
        model=resolved_model,
        content=[{"type": "text", "text": prompt}],
        timeout=timeout,
        max_tokens=4096,
        thinking=thinking,
    )
    return _parse_json_object(text)


def analyze_video_files(
    video_items: list[dict],
    *,
    model: str | None = None,
    profile: str = "knowledge",
    custom_prompt: str | None = None,
    fps: float = 0.5,
    upload_timeout: int = 900,
    response_timeout: int = 600,
    concurrency: int = 2,
    progress: Callable[[str], None] | None = None,
    cache_dir: Path | None = None,
    force: bool = False,
    thinking: str = "disabled",
    backend: str = "bailian",
) -> tuple[list[dict], list[dict]]:
    """Frame-sampling fallback for gateways without Ark's Files/Responses API.

    Each prepared clip is decoded locally at ~1 frame every 2 seconds (bounded by
    ``max_frames``) and the frames are analysed as images. Timestamps are shifted
    back onto the original timeline; ``source_id`` keeps the clip identity.
    """
    del upload_timeout, cache_dir, force  # frame sampling has its own local cache
    from .frame_sampler import sample_frames

    if not video_items:
        return [], []
    resolved_model = resolve_model(backend, model)
    interval = max(0.5, 1.0 / max(0.2, min(fps, 5.0)))
    notes: list[dict] = []
    errors: list[dict] = []
    for index, item in enumerate(video_items, start=1):
        label = str(item.get("id") or f"video-{index}")
        prefix = f"[{index}/{len(video_items)}] {label}"
        try:
            source_start = int(item.get("start_ms") or 0)
            duration_ms = max(0, int(item.get("end_ms") or source_start) - source_start)
            if duration_ms <= 0:
                raise RuntimeError("Video item has no positive duration.")
            max_frames = max(4, min(48, int(round(duration_ms / 1000.0 * max(0.2, min(fps, 5.0))))))
            with tempfile.TemporaryDirectory(prefix="vision-frames-") as temp_dir:
                if progress:
                    progress(f"{prefix}：本地抽帧，约 {max_frames} 帧")
                frames, _sampling = sample_frames(
                    Path(item["path"]),
                    Path(temp_dir),
                    interval_seconds=interval,
                    max_frames=max_frames,
                    scene_threshold=0.32,
                )
                for frame in frames:
                    frame["id"] = f"{label}-{frame.get('id') or 'frame'}"
                batch_notes, batch_errors = analyze_frames(
                    frames,
                    model=resolved_model,
                    profile=profile,
                    custom_prompt=custom_prompt,
                    batch_size=4,
                    timeout=response_timeout,
                    backend=backend,
                )
            for note in batch_notes:
                note["start_ms"] = source_start + int(note.get("timestamp_ms") or 0)
                note["end_ms"] = note["start_ms"]
                note["timestamp_ms"] = note["start_ms"]
                note["source_id"] = label
                note["evidence_kind"] = "video-frame"
            notes.extend(batch_notes)
            errors.extend(batch_errors)
            if progress:
                progress(f"{prefix}：抽帧分析完成，得到 {len(batch_notes)} 条视觉记录")
        except (RuntimeError, OSError, ValueError, TypeError) as exc:
            errors.append({"evidence_ids": [label], "error": str(exc)})
    notes.sort(key=lambda note: (note["start_ms"], note.get("id") or ""))
    return notes, errors


def _chat_text(
    *,
    backend: str,
    api_key: str,
    model: str,
    content: list[dict],
    timeout: int,
    max_tokens: int,
    thinking: str = "disabled",
) -> str:
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
    }
    if thinking in {"disabled", "auto", "enabled"}:
        payload["enable_thinking"] = thinking != "disabled"
    response = _post_json(
        f"{DEFAULT_BASE_URLS[backend]}/chat/completions",
        payload,
        api_key=api_key,
        timeout=timeout,
        label=f"{backend} chat/completions",
    )
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError(f"{backend} response did not include choices[0].")
    message = choices[0].get("message")
    value = message.get("content") if isinstance(message, dict) else None
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, list):
        parts = [
            str(block.get("text") or "").strip()
            for block in value
            if isinstance(block, dict) and block.get("type") in {"text", "output_text"}
        ]
        joined = "\n".join(part for part in parts if part)
        if joined:
            return joined
    raise RuntimeError(f"{backend} response did not include assistant text content.")


def _post_json(url: str, payload: dict, *, api_key: str, timeout: int, label: str) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise RuntimeError(f"{label} returned an unexpected JSON value.")
            return parsed
        except HTTPError as exc:
            retryable = exc.code in {429, 500, 502, 503, 504}
            try:
                detail = exc.read(16384).decode("utf-8", errors="replace")
                message = json.loads(detail).get("error", {}).get("message") or ""
            except Exception:
                message = ""
            error = RuntimeError(f"{label} returned HTTP {exc.code}" + (f": {message[:200]}" if message else ""))
            if not retryable or attempt == 2:
                raise error from exc
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise RuntimeError(f"{label} timed out.") from exc
            raise RuntimeError(f"Could not reach {label}: {type(exc.reason).__name__}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"{label} timed out.") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{label} returned non-JSON data; response body was redacted.") from exc
        time.sleep(2**attempt)
    raise RuntimeError(f"Unreachable retry state for {label}")


def _parse_json_object(text: str) -> dict:
    from .doubao import _parse_json_object as parse

    return parse(text)


def analyze_video_native(
    video_items: list[dict],
    *,
    model: str | None = None,
    profile: str = "knowledge",
    custom_prompt: str | None = None,
    timeout: int = 600,
    progress: Callable[[str], None] | None = None,
    backend: str = "bailian",
) -> tuple[list[dict], list[dict]]:
    """Send prepared clips as native ``video_url`` blocks.

    Only the Bailian omni compatible endpoint is known to accept native video in
    this workflow. Inputs come from ``item['public_url']`` when a caller has a
    reachable HTTP(S) link, otherwise from an inline base64 data URL for files up
    to :data:`MAX_INLINE_VIDEO_BYTES`. Items that satisfy neither are reported as
    errors so the caller can fall back to frame sampling.
    """
    api_key = backend_key(backend)
    if not api_key:
        raise RuntimeError(f"No credential for vision backend '{backend}'.")
    resolved_model = resolve_model(backend, model)
    notes: list[dict] = []
    errors: list[dict] = []
    total = len(video_items)
    for index, item in enumerate(video_items, start=1):
        label = str(item.get("id") or f"video-{index}")
        prefix = f"[{index}/{total}] {label}"
        try:
            url = _video_input_url(item)
            if not url:
                raise RuntimeError(
                    "No public video URL and the prepared file exceeds the inline limit; "
                    "falling back to frame sampling."
                )
            if progress:
                progress(f"{prefix}：原生视频理解（{resolved_model}）")
            text = _chat_text(
                backend=backend,
                api_key=api_key,
                model=resolved_model,
                content=[
                    {"type": "video_url", "video_url": {"url": url}},
                    {"type": "text", "text": _video_prompt(item, profile, custom_prompt)},
                ],
                timeout=timeout,
                max_tokens=8192,
            )
            parsed = _parse_video_notes(
                {"status": "completed", "output_text": text},
                item,
                model=resolved_model,
                profile=profile,
            )
            for note in parsed:
                note["backend"] = backend
                note["evidence_kind"] = "native-video"
            notes.extend(parsed)
            if progress:
                progress(f"{prefix}：原生视频解析完成，得到 {len(parsed)} 条视觉记录")
        except (RuntimeError, OSError, ValueError, TypeError) as exc:
            errors.append({"evidence_ids": [label], "error": str(exc)})
    notes.sort(key=lambda note: (note["start_ms"], note.get("id") or ""))
    return notes, errors


def _video_input_url(item: dict) -> str | None:
    """Return a ``video_url`` payload for one prepared video item, or ``None``.

    Only a caller-supplied HTTP(S) link and an inline base64 data URL for files
    up to :data:`MAX_INLINE_VIDEO_BYTES` are supported. Larger local files are
    reported as unusable so the caller falls back to frame sampling.
    """
    direct = str(item.get("public_url") or "").strip()
    if direct.startswith(("http://", "https://")):
        return direct
    path = Path(str(item.get("path") or ""))
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_INLINE_VIDEO_BYTES:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = "video/mp4" if path.suffix.lower() == ".mp4" else "video/quicktime"
    return f"data:{mime};base64,{encoded}"
