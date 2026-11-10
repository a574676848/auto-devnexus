"""Temporary public hosting for oversized local videos on Aliyun OSS.

The Bailian omni endpoint accepts native ``video_url`` input, but only for a
reachable HTTP(S) link or an inline base64 payload up to
:data:`openai_vision.MAX_INLINE_VIDEO_BYTES`. Local files above that limit have
to be published somewhere first.

This module assumes an STS role, streams the file to one object with an
object-level ``public-read`` ACL, and returns the plain object URL. The caller
deletes it as soon as the model request finishes, so the public window is short
and the object name is a random UUID.

Credentials live outside the skill, in the first readable path of
:data:`CONFIG_CANDIDATES`::

    {
      "accessKeyId": "...",
      "accessKeySecret": "...",
      "roleArn": "acs:ram::<account>:role/<role>",
      "roleSessionName": "RamOssTest",
      "bucket": "<your-bucket>",
      "region": "cn-beijing",
      "prefix": "tmp/video-downloader/",
      "durationSeconds": 900
    }
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import http.client
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

CONFIG_CANDIDATES = (
    Path.home() / ".axon" / "data" / "video-downloader" / "oss-temp-host.json",
    Path.home() / ".config" / "kangarooking-skills" / "video-downloader" / "oss-temp-host.json",
)

STS_VERSION = "2015-04-01"
OBJECT_ACL = "public-read"
UPLOAD_TIMEOUT_SECONDS = 600
CHUNK_BYTES = 1 << 20
CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/x-m4v",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}

_CREDENTIAL_LOCK = threading.Lock()
_CREDENTIAL_CACHE: tuple[str, str, str, float] | None = None


def load_config() -> dict | None:
    """Return the first usable credential file, or ``None`` when unconfigured."""
    for candidate in CONFIG_CANDIDATES:
        try:
            if candidate.is_file():
                config = json.loads(candidate.read_text(encoding="utf-8"))
                if config.get("accessKeyId") and config.get("bucket"):
                    return config
        except (OSError, ValueError):
            continue
    return None


def available() -> bool:
    return load_config() is not None


def _percent_encode(value: str) -> str:
    return urllib.parse.quote(str(value), safe="-_.~")


def _assume_role(config: dict) -> tuple[str, str, str]:
    """Assume the configured role, caching the temporary credential until expiry."""
    global _CREDENTIAL_CACHE
    with _CREDENTIAL_LOCK:
        if _CREDENTIAL_CACHE and _CREDENTIAL_CACHE[3] - 60 > time.time():
            return _CREDENTIAL_CACHE[0], _CREDENTIAL_CACHE[1], _CREDENTIAL_CACHE[2]

        endpoint = config.get("stsEndpoint") or f"https://sts.{config['region']}.aliyuncs.com/"
        params = {
            "Format": "JSON",
            "Version": STS_VERSION,
            "AccessKeyId": config["accessKeyId"],
            "SignatureMethod": "HMAC-SHA1",
            "SignatureVersion": "1.0",
            "SignatureNonce": uuid.uuid4().hex,
            "Timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Action": "AssumeRole",
            "RoleArn": config["roleArn"],
            "RoleSessionName": config.get("roleSessionName") or "VideoDownloaderTempHost",
            "DurationSeconds": str(int(config.get("durationSeconds") or 900)),
        }
        canonical = "&".join(
            f"{_percent_encode(k)}={_percent_encode(v)}" for k, v in sorted(params.items())
        )
        to_sign = "POST&%2F&" + _percent_encode(canonical)
        digest = hmac.new(
            (config["accessKeySecret"] + "&").encode(), to_sign.encode(), hashlib.sha1
        ).digest()
        params["Signature"] = base64.b64encode(digest).decode()

        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode(params).encode(),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
        credentials = payload["Credentials"]
        expires = _parse_expiry(credentials.get("Expiration"))
        _CREDENTIAL_CACHE = (
            credentials["AccessKeyId"],
            credentials["AccessKeySecret"],
            credentials["SecurityToken"],
            expires,
        )
        return _CREDENTIAL_CACHE[0], _CREDENTIAL_CACHE[1], _CREDENTIAL_CACHE[2]


def _parse_expiry(value: str | None) -> float:
    if not value:
        return time.time() + 600
    try:
        moment = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return time.time() + 600
    return moment.replace(tzinfo=dt.timezone.utc).timestamp()


def _oss_date() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def _signed_headers(method: str, config: dict, key: str, content_type: str,
                    credential: tuple[str, str, str], extra: dict | None = None) -> dict:
    access_key, secret_key, token = credential
    date = _oss_date()
    oss_headers = {"x-oss-security-token": token, **(extra or {})}
    canonical = "".join(
        f"{name.lower()}:{value}\n" for name, value in sorted(oss_headers.items())
    )
    resource = f"/{config['bucket']}/{key}"
    to_sign = "\n".join([method, "", content_type, date, canonical + resource])
    digest = hmac.new(secret_key.encode(), to_sign.encode(), hashlib.sha1).digest()
    headers = dict(oss_headers)
    headers["Authorization"] = f"OSS {access_key}:{base64.b64encode(digest).decode()}"
    headers["Date"] = date
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _object_url(config: dict, key: str) -> str:
    host = f"{config['bucket']}.oss-{config['region']}.aliyuncs.com"
    return f"https://{host}/{urllib.parse.quote(key, safe='/')}"


def upload_for_public_url(path: Path) -> tuple[str | None, str | None]:
    """Publish ``path`` as one public-read object.

    Returns ``(url, object_key)``; ``(None, None)`` when the feature is not
    configured or the upload failed, so the caller can fall back to frame
    sampling instead of aborting the run.
    """
    config = load_config()
    if config is None:
        return None, None
    if not path.is_file():
        return None, None
    try:
        credential = _assume_role(config)
        key = f"{config.get('prefix') or 'tmp/video-downloader/'}{uuid.uuid4().hex}{path.suffix.lower()}"
        _put_object(config, key, path, credential)
        return _object_url(config, key), key
    except (OSError, ValueError, KeyError, urllib.error.URLError, http.client.HTTPException) as exc:
        print(f"[temp-host] 上传失败，改用本地抽帧：{exc}", flush=True)
        return None, None


def _put_object(config: dict, key: str, path: Path, credential: tuple[str, str, str]) -> None:
    content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
    headers = _signed_headers("PUT", config, key, content_type, credential,
                              {"x-oss-object-acl": OBJECT_ACL})
    size = path.stat().st_size
    if size > 5 * 1024 ** 3:
        raise ValueError("file exceeds the 5 GiB single-PUT limit")

    host = f"{config['bucket']}.oss-{config['region']}.aliyuncs.com"
    connection = http.client.HTTPSConnection(host, timeout=UPLOAD_TIMEOUT_SECONDS)
    try:
        connection.putrequest("PUT", "/" + urllib.parse.quote(key, safe="/"), skip_accept_encoding=True)
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.putheader("Content-Length", str(size))
        connection.endheaders()
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK_BYTES):
                connection.send(chunk)
        response = connection.getresponse()
        detail = response.read()[:300].decode(errors="replace")
        if response.status != 200:
            raise ValueError(f"OSS PUT {response.status}: {detail}")
    finally:
        connection.close()


def delete_public_object(key: str) -> bool:
    """Best-effort removal of a temporary object. Never raises."""
    config = load_config()
    if config is None or not key:
        return False
    try:
        credential = _assume_role(config)
        headers = _signed_headers("DELETE", config, key, "", credential)
        request = urllib.request.Request(_object_url(config, key), method="DELETE", headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status in (200, 204)
    except (OSError, ValueError, KeyError, urllib.error.URLError, http.client.HTTPException) as exc:
        print(f"[temp-host] 临时对象删除失败，请手动清理 {key}：{exc}", flush=True)
        return False
