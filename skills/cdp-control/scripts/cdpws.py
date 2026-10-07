"""Transport layer for cdp.py: HTTP surface, target selection, WebSocket framing.

Split out of cdp.py so each file stays small and single-purpose. Imported by
cdpui.py and cdp.py; not meant to be run directly.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
DEFAULT_PORTS = (9333, 9222, 9229, 9444, 9223, 8315)



class CdpError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _prepare_stdout() -> None:
    """Page text can be any Unicode; make sure printing it never crashes."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def emit(line: str) -> None:
    _prepare_stdout()
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        sys.stdout.buffer.write(line.encode("utf-8", "replace") + b"\n")
        sys.stdout.flush()


def emit_ok(payload: str) -> None:
    emit("OK:" + payload)


def emit_err(code: str, message: str) -> None:
    emit("ERR:%s:%s" % (code, " ".join(str(message).split())))


def compact(value) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True, default=str)


# ---------------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------------
def http_json(port: int, path: str, method: str = "GET", timeout: float = 5.0):
    url = "http://127.0.0.1:%d%s" % (port, path)
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def http_text(port: int, path: str, method: str = "GET", timeout: float = 5.0) -> str:
    """Some /json endpoints answer with plain text, not JSON.

    /json/close/<id> replies with 'Target is closing'. Parsing that as JSON
    would report a failure for an action that in fact succeeded, which is the
    worst possible bug in a tool whose whole job is producing trustworthy
    evidence. Read the body without assuming its shape.
    """
    url = "http://127.0.0.1:%d%s" % (port, path)
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def resolve_port(requested: int) -> int:
    if requested:
        try:
            http_json(requested, "/json/version", timeout=3.0)
            return requested
        except Exception as exc:
            raise CdpError("no-endpoint", "port %d is not a live CDP endpoint: %s" % (requested, exc))
    for candidate in DEFAULT_PORTS:
        try:
            http_json(candidate, "/json/version", timeout=1.0)
            return candidate
        except Exception:
            continue
    raise CdpError("no-endpoint", "no CDP endpoint found; probed %s. Pass --port."
                   % ",".join(str(p) for p in DEFAULT_PORTS))


def get_targets(port: int):
    data = http_json(port, "/json", timeout=5.0)
    return data if isinstance(data, list) else [data]


def select_target(port: int, target_type: str, url_match: str,
                  target_id: str = "", allow_first: bool = False):
    all_targets = get_targets(port)
    if target_id:
        for t in all_targets:
            if t.get("id") == target_id:
                return t
        raise CdpError("no-target", "no target with id=%s on port %d" % (target_id, port))

    cands = [t for t in all_targets if t.get("type") == target_type]
    if url_match:
        cands = [t for t in cands if url_match in (t.get("url") or "")]
    if not cands:
        return None
    # Driving the wrong tab silently is the worst failure mode here: opening a
    # new tab reorders /json, so "the first page" is not a stable identity.
    # Refuse to guess when several targets qualify.
    if len(cands) > 1 and not allow_first:
        listing = " ; ".join("[%s] %s" % (t.get("id"), t.get("url")) for t in cands)
        raise CdpError(
            "ambiguous-target",
            "%d targets match type=%s urlMatch='%s' -> %s . Pin one with --url-match or "
            "--target-id, or pass --first to accept the first." % (len(cands), target_type, url_match, listing),
        )
    real = [t for t in cands if t.get("url") and t.get("url") != "about:blank"]
    return real[0] if real else cands[0]


# ---------------------------------------------------------------------------
# Minimal RFC 6455 client. Client frames must be masked; pings get ponged;
# fragmented messages are reassembled before parsing.
# ---------------------------------------------------------------------------
class CdpSocket:
    def __init__(self, ws_url: str, timeout: float):
        parsed = urllib.parse.urlparse(ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        try:
            self.sock = socket.create_connection((host, port), timeout=timeout)
        except OSError as exc:
            raise CdpError("connect-failed", "websocket connect failed: %s" % exc)
        self.sock.settimeout(timeout)
        self._buf = b""
        self._seq = 0

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            "GET %s HTTP/1.1\r\n"
            "Host: %s:%d\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n" % (path, host, port, key)
        )
        try:
            self.sock.sendall(handshake.encode("ascii"))
            head = self._read_until(b"\r\n\r\n")
        except (OSError, socket.timeout) as exc:
            raise CdpError("connect-failed", "websocket handshake failed: %s" % exc)
        status = head.split(b"\r\n", 1)[0].decode("latin-1")
        if "101" not in status:
            raise CdpError("connect-failed", "handshake rejected: %s" % status)

    # -- raw plumbing ------------------------------------------------------
    def _read_until(self, marker: bytes) -> bytes:
        while marker not in self._buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise CdpError("connect-failed", "endpoint closed during handshake")
            self._buf += chunk
        head, _, rest = self._buf.partition(marker)
        self._buf = rest
        return head

    def _read_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                raise CdpError("timeout", "timed out while reading from the endpoint")
            except OSError as exc:
                raise CdpError("connect-failed", "socket error: %s" % exc)
            if not chunk:
                raise CdpError("connect-failed", "peer closed the connection")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        header = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack("!H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack("!Q", n)
        mask = os.urandom(4)
        header += mask
        masked = bytes(payload[i] ^ mask[i % 4] for i in range(n))
        try:
            self.sock.sendall(bytes(header) + masked)
        except OSError as exc:
            raise CdpError("connect-failed", "send failed: %s" % exc)

    def _read_message(self) -> str:
        parts = []
        while True:
            b1, b2 = self._read_exact(2)
            fin = b1 & 0x80
            opcode = b1 & 0x0F
            masked = b2 & 0x80
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(length) if length else b""
            if mask:
                payload = bytes(payload[i] ^ mask[i % 4] for i in range(length))
            if opcode == 0x9:            # ping -> pong, keep waiting
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:            # pong, ignore
                continue
            if opcode == 0x8:            # close
                raise CdpError("connect-failed", "peer closed the connection")
            parts.append(payload)
            if fin:
                break
        return b"".join(parts).decode("utf-8", errors="replace")

    def close(self) -> None:
        try:
            self._send_frame(0x8, b"")
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

    # -- protocol layer ----------------------------------------------------
    def request(self, method: str, params=None, budget_ms: int = 30000):
        self._seq += 1
        mid = self._seq
        body = json.dumps({"id": mid, "method": method, "params": params or {}},
                          separators=(",", ":"), ensure_ascii=False)
        self._send_frame(0x1, body.encode("utf-8"))

        deadline = time.monotonic() + budget_ms / 1000.0
        while time.monotonic() < deadline:
            self.sock.settimeout(max(0.2, deadline - time.monotonic()))
            text = self._read_message()
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                continue
            # Event frames carry no id; skip them instead of misreading them
            # as a reply. This is the single most common parser bug here.
            if obj.get("id") != mid:
                continue
            if "error" in obj:
                err = obj["error"] or {}
                raise CdpError("protocol-error", "%s failed: %s" % (method, err.get("message", err)))
            return obj.get("result", {})
        raise CdpError("timeout", "timed out waiting for the %s reply" % method)

