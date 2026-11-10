"""Volcano Ark streaming ASR client (doubao-seed-asr-2.0 / SAUC bigmodel).

Uses the binary WebSocket protocol documented for the Agent Plan speech
endpoints. ``bigmodel_nostream`` means "streaming *output*": the client sends the
whole audio file and receives incremental results, which is exactly what a batch
transcriber needs.
"""

from __future__ import annotations

import gzip
import json
import os
import struct
import uuid
from pathlib import Path


ARK_ASR_URL = "wss://openspeech.bytedance.com/api/v3/plan/sauc/bigmodel_nostream"
ARK_ASR_RESOURCE_ID = "volc.seedasr.sauc.duration"
ARK_ASR_DEFAULT_MODEL = "doubao-seed-asr-2.0"

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

FLAG_NONE = 0b0000
FLAG_POS_SEQUENCE = 0b0001
FLAG_LAST_NO_SEQUENCE = 0b0010
FLAG_LAST_WITH_SEQUENCE = 0b0011

JSON_SERIALIZATION = 0b0001
NO_SERIALIZATION = 0b0000
GZIP_COMPRESSION = 0b0001

CHUNK_BYTES = 3200


class ArkAsrError(RuntimeError):
    """Raised when the Ark ASR service rejects or aborts a request."""


def resolve_api_key() -> str | None:
    """Return ARK_API_KEY from the environment, else from the Ark CLI identity store."""
    value = os.environ.get("ARK_API_KEY")
    if value:
        return value
    for path in sorted((Path.home() / ".arkcli" / "identities").glob("*/apikey.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        key = str(payload.get("api_key") or "").strip()
        if key:
            return key
    return None


def transcribe_with_ark(
    audio_path: Path,
    transcript_path: Path,
    raw_json_path: Path,
    *,
    model: str = ARK_ASR_DEFAULT_MODEL,
    language: str = "auto",
    prompt: str | None = None,
    timeout: int = 1800,
) -> None:
    api_key = resolve_api_key()
    if not api_key:
        raise ArkAsrError(
            "ARK_API_KEY is required for the Ark ASR backend "
            "(run `arkcli auth login volc-sso` or set ARK_API_KEY)."
        )
    if not audio_path.is_file():
        raise ArkAsrError(f"Audio file does not exist: {audio_path}")
    payload = _transcribe(
        audio_path,
        api_key=api_key,
        language=language,
        prompt=prompt,
        timeout=timeout,
        audio_format=_audio_format(audio_path),
    )
    result = payload.get("result") or {}
    text = str(result.get("text") or "").strip()
    if not text:
        raise ArkAsrError("Ark ASR returned an empty transcript.")
    utterances = result.get("utterances") or []
    segments = []
    for item in utterances:
        if not isinstance(item, dict):
            continue
        utterance_text = str(item.get("text") or "").strip()
        if not utterance_text:
            continue
        segments.append(
            {
                "start": _ms_to_seconds(item.get("start_time")),
                "end": _ms_to_seconds(item.get("end_time")),
                "text": utterance_text,
                "confidence": item.get("confidence"),
                "timestamp_precision": "segment",
            }
        )
    transcript_path.write_text(
        "\n".join(seg["text"] for seg in segments).strip() + "\n" if segments else text + "\n",
        encoding="utf-8",
    )
    raw_json_path.write_text(
        json.dumps(
            {
                "backend": "ark",
                "model": model,
                "resource_id": ARK_ASR_RESOURCE_ID,
                "language": language,
                "prompt": prompt,
                "text": text,
                "segments": segments,
                "provider_response": payload,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _transcribe(
    path: Path,
    *,
    api_key: str,
    language: str,
    prompt: str | None,
    timeout: int,
    audio_format: str = "mp3",
) -> dict:
    try:
        from websockets.sync.client import connect
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ArkAsrError("The 'websockets' package is required for Ark ASR (pip install websockets).") from exc

    headers = {
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": ARK_ASR_RESOURCE_ID,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
    with connect(ARK_ASR_URL, additional_headers=headers, max_size=None, open_timeout=30, close_timeout=10) as socket:
        socket.send(_full_client_request(language=language, prompt=prompt, audio_format=audio_format))
        chunks: list[bytes] = []
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(CHUNK_BYTES)
                if not chunk:
                    break
                chunks.append(chunk)
        if not chunks:
            raise ArkAsrError(f"Audio file is empty: {path}")
        # The full client request already consumed sequence 1; audio starts at 2.
        # The final packet is marked both by the last flag and by a negative sequence.
        for index, chunk in enumerate(chunks, start=2):
            last = index == len(chunks) + 1
            socket.send(_audio_frame(chunk, sequence=(-index if last else index), last=last))
        return _read_result(socket, timeout)


def _read_result(socket, timeout: int) -> dict:
    while True:
        try:
            message = socket.recv(timeout=timeout)
        except TimeoutError as exc:
            raise ArkAsrError("Ark ASR timed out before returning a final result.") from exc
        if not isinstance(message, (bytes, bytearray)):
            continue
        payload = _parse_message(bytes(message), allow_error=False)
        if payload.pop("_ack", False):
            continue
        result = payload.get("result")
        if isinstance(result, dict) and (str(result.get("text") or "").strip() or payload.get("_is_last")):
            payload.pop("_is_last", None)
            return payload
        if payload.pop("_is_last", False):
            return payload


def _full_client_request(*, language: str, prompt: str | None, audio_format: str = "mp3") -> bytes:
    request: dict = {
        "model_name": "bigmodel",
        "enable_itn": True,
        "enable_punc": True,
        "enable_ddc": True,
        "show_utterances": True,
        "result_type": "full",
    }
    if language and language.lower() not in {"auto", ""}:
        request["language"] = language
    if prompt:
        request["corpus"] = {"context": prompt[:800]}
    payload = {
        "user": {"uid": "video-downloader"},
        "audio": {"format": audio_format, "codec": "raw", "rate": 16000, "bits": 16, "channel": 1},
        "request": request,
    }
    body = gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    header = _header(
        message_type=FULL_CLIENT_REQUEST,
        flags=FLAG_POS_SEQUENCE,
        serialization=JSON_SERIALIZATION,
        compression=GZIP_COMPRESSION,
    )
    return header + struct.pack(">i", 1) + struct.pack(">I", len(body)) + body


def _audio_frame(chunk: bytes, *, sequence: int, last: bool) -> bytes:
    flags = FLAG_LAST_WITH_SEQUENCE if last else FLAG_POS_SEQUENCE
    body = gzip.compress(chunk) if chunk else b""
    header = _header(
        message_type=AUDIO_ONLY_REQUEST,
        flags=flags,
        serialization=NO_SERIALIZATION,
        compression=GZIP_COMPRESSION,
    )
    return header + struct.pack(">i", sequence) + struct.pack(">I", len(body)) + body


def _header(*, message_type: int, flags: int, serialization: int, compression: int) -> bytes:
    return bytes(
        [
            (PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE,
            (message_type << 4) | flags,
            (serialization << 4) | compression,
            0x00,
        ]
    )


def _parse_message(data: bytes, *, allow_error: bool) -> dict:
    if len(data) < 4:
        raise ArkAsrError("Ark ASR returned a truncated frame.")
    header_size = (data[0] & 0x0F) * 4
    message_type = data[1] >> 4
    flags = data[1] & 0x0F
    compression = data[2] & 0x0F
    offset = header_size
    sequence = None
    if flags in {FLAG_POS_SEQUENCE, FLAG_LAST_WITH_SEQUENCE}:
        if len(data) < offset + 4:
            raise ArkAsrError("Ark ASR frame is missing its sequence number.")
        sequence = struct.unpack(">i", data[offset : offset + 4])[0]
        offset += 4
    if message_type == SERVER_ERROR_RESPONSE:
        code, message = _error_body(data, offset=offset, compression=compression)
        raise ArkAsrError(f"Ark ASR error {code}: {message}")
    if message_type == SERVER_ACK:
        return {"_ack": True, "sequence": sequence}
    if len(data) < offset + 4:
        return {"_is_last": flags in {FLAG_LAST_NO_SEQUENCE, FLAG_LAST_WITH_SEQUENCE}, "sequence": sequence}
    size = struct.unpack(">I", data[offset : offset + 4])[0]
    offset += 4
    body = data[offset : offset + size]
    if compression == GZIP_COMPRESSION and body:
        try:
            body = gzip.decompress(body)
        except OSError as exc:
            raise ArkAsrError("Ark ASR payload was not valid gzip data.") from exc
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArkAsrError("Ark ASR payload was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ArkAsrError("Ark ASR returned an unexpected payload type.")
    payload["_is_last"] = flags in {FLAG_LAST_NO_SEQUENCE, FLAG_LAST_WITH_SEQUENCE}
    payload["sequence"] = sequence
    return payload


def _error_body(data: bytes, *, offset: int, compression: int) -> tuple[int, str]:
    if len(data) < offset + 8:
        return -1, "malformed error frame"
    code = struct.unpack(">I", data[offset : offset + 4])[0]
    size = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
    body = data[offset + 8 : offset + 8 + size]
    if compression == GZIP_COMPRESSION and body:
        try:
            body = gzip.decompress(body)
        except OSError:
            pass
    return code, body.decode("utf-8", errors="replace")[:400]


def _ms_to_seconds(value) -> float | None:
    try:
        return round(float(value) / 1000.0, 3)
    except (TypeError, ValueError):
        return None


def _audio_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"mp3", "wav", "ogg", "pcm"}:
        return suffix
    return "mp3"
