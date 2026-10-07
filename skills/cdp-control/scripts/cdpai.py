"""Laya decision-model bridge for cdp.py.

Laya (https://github.com/NandhaKishorM/laya) is a non-autoregressive System-1
decision engine served over the TypeSafe Jev /v1/systemone protocol. It answers
three typed questions in one forward pass:

    choice  pick one label out of a criteria map   -> answers[name].choice
    score   place the input on an ordinal scale    -> answers[name].score
    noul    calibrated yes/no strength, 0..1       -> answers[name].noul

Where this earns its place in a CDP session: CSS selectors cannot tell a human
which of five similarly-styled buttons is "the submit button", and a text match
breaks the moment the UI is localised or the class names are hashed. Laya turns
that into a decision over labelled candidates, and returns calibrated numbers
you can threshold instead of a bare guess.

Configuration is environment/file driven on purpose. Never hardcode a service
address in this file: it ships to other machines and to public repositories.
Resolution order, first hit wins:

    base URL   --laya-url   >  CDP_LAYA_BASE_URL  >  LAYA_BASE_URL  >  config file
    api key    --laya-key   >  CDP_LAYA_API_KEY   >  LAYA_API_KEY   >  config file
    timeout    --laya-timeout  >  CDP_LAYA_TIMEOUT  >  config file  >  120s

config file path:  $CDP_LAYA_CONFIG, else ~/.config/cdp-control/laya.json

    {"base_url": "http://<host>:<port>", "api_key": "<token>", "timeout_seconds": 120}

The API key is optional and only needed when the server was started with its own
auth token configured.
"""

from __future__ import annotations

import ipaddress
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from cdpws import CdpError

DEFAULT_TIMEOUT_SECONDS = 120.0
CONFIG_ENV_PATH = "CDP_LAYA_CONFIG"
BASE_URL_ENV = ("CDP_LAYA_BASE_URL", "LAYA_BASE_URL")
API_KEY_ENV = ("CDP_LAYA_API_KEY", "LAYA_API_KEY")
TIMEOUT_ENV = "CDP_LAYA_TIMEOUT"


def default_config_path() -> str:
    """A per-user location that works the same on Windows, macOS and Linux."""
    return os.path.join(os.path.expanduser("~"), ".config", "cdp-control", "laya.json")


def resolve_config(cli_url: str = "", cli_key: str = "", cli_timeout: float = 0.0) -> dict:
    url = (cli_url or "").strip()
    key = (cli_key or "").strip()
    timeout = float(cli_timeout or 0.0)
    origin = {"url": "flag" if url else "", "key": "flag" if key else ""}

    if not url:
        for name in BASE_URL_ENV:
            value = (os.environ.get(name) or "").strip()
            if value:
                url, origin["url"] = value, "env:" + name
                break
    if not key:
        for name in API_KEY_ENV:
            value = (os.environ.get(name) or "").strip()
            if value:
                key, origin["key"] = value, "env:" + name
                break
    if not timeout:
        raw = (os.environ.get(TIMEOUT_ENV) or "").strip()
        if raw:
            try:
                timeout = float(raw)
            except ValueError:
                raise CdpError("laya-bad-config", "%s is not a number: %r" % (TIMEOUT_ENV, raw))

    path = os.path.expanduser((os.environ.get(CONFIG_ENV_PATH) or "").strip() or default_config_path())
    if (not url or not key or not timeout) and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise CdpError("laya-bad-config", "cannot read %s: %s" % (path, exc))
        if not isinstance(data, dict):
            raise CdpError("laya-bad-config", "%s must contain a JSON object" % path)
        if not url:
            url = str(data.get("base_url") or data.get("baseUrl") or "").strip()
            if url:
                origin["url"] = "file:" + path
        if not key:
            key = str(data.get("api_key") or data.get("apiKey") or "").strip()
            if key:
                origin["key"] = "file:" + path
        if not timeout:
            try:
                timeout = float(data.get("timeout_seconds") or 0.0)
            except (TypeError, ValueError):
                timeout = 0.0

    if not url:
        raise CdpError(
            "laya-unconfigured",
            "no Laya base URL configured. Pass --laya-url, or set %s / %s, or write "
            '{"base_url": "http://<host>:<port>"} to %s' % (BASE_URL_ENV[0], BASE_URL_ENV[1], path),
        )

    return {
        "base_url": url.rstrip("/"),
        "api_key": key,
        "timeout": timeout or DEFAULT_TIMEOUT_SECONDS,
        "config_path": path,
        "origin": origin,
    }


def is_private_host(host: str) -> bool:
    if not host:
        return False
    lowered = host.lower().strip("[]")
    if lowered in ("localhost", "::1") or lowered.endswith(".local") or lowered.endswith(".internal"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        # A bare single-label name is a LAN hostname, not a public FQDN.
        return "." not in lowered
    return address.is_private or address.is_loopback or address.is_link_local


def build_opener(base_url: str):
    """Bypass the system proxy for LAN/loopback services.

    A TUN-mode proxy or a corporate HTTP_PROXY will happily swallow requests to
    a private address and fail with a confusing timeout. Talking to a machine on
    your own network through a proxy is never what you meant, so opt out.
    """
    host = urllib.parse.urlparse(base_url).hostname or ""
    if is_private_host(host):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def call(config: dict, path: str, body: dict | None = None, timeout: float = 0.0) -> dict:
    url = config["base_url"] + path
    headers = {"accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    if config.get("api_key"):
        headers["Authorization"] = "Bearer " + config["api_key"]

    request = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
    budget = timeout or config["timeout"]
    try:
        with build_opener(config["base_url"]).open(request, timeout=budget) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = " ".join(exc.read().decode("utf-8", errors="replace").split())[:400]
        raise CdpError("laya-http-%d" % exc.code, "%s from %s: %s" % (exc.code, url, detail))
    except urllib.error.URLError as exc:
        raise CdpError("laya-unreachable",
                       "cannot reach %s: %s . Check the base URL, that the host is reachable "
                       "from here, and that no proxy is intercepting private traffic."
                       % (url, getattr(exc, "reason", exc)))
    except OSError as exc:
        raise CdpError("laya-unreachable", "cannot reach %s: %s" % (url, exc))

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CdpError("laya-bad-response", "non-JSON reply from %s: %s" % (url, exc))
    if not isinstance(parsed, dict):
        raise CdpError("laya-bad-response", "expected a JSON object from %s" % url)
    return parsed


def health(config: dict) -> dict:
    return call(config, "/health")


def ask(config: dict, state_text: str, questions: dict, timeout: float = 0.0) -> dict:
    """One forward pass for every question, which matters on CPU backends."""
    payload = {"state": {"body": state_text}, "questions": questions}
    return call(config, "/v1/systemone", payload, timeout=timeout)


def choice_question(instructions: str, criteria: dict) -> dict:
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score_question(instructions: str, criteria: list) -> dict:
    return {"type": "score", "instructions": instructions, "criteria": list(criteria)}


def noul_question(instructions: str) -> dict:
    return {"type": "noul", "instructions": instructions}


def answer_probability(answer: dict) -> float:
    """The probability of the answer the model actually gave.

    `confidence` is the margin-style score the service reports; `answer_confidence`
    is the mass on the winning label, which is the number a caller wants when
    deciding whether to trust a single pick.
    """
    for field in ("answer_confidence", "confidence", "noul", "action"):
        value = answer.get(field)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict) and isinstance(value.get("act_probability"), (int, float)):
            return float(value["act_probability"])
    return 0.0
