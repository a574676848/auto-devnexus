#!/usr/bin/env python3
"""cdp.py - one-shot Chrome DevTools Protocol driver.

Drives any Chromium-based surface that exposes a DevTools endpoint:
WebView2 / Tauri / Electron windows, Chrome, Edge, headless Chromium.

Cross-platform by construction: Python 3.8+ standard library ONLY, no pip
install, no third-party WebSocket package. The WebSocket client below is a
minimal RFC 6455 implementation so the same file runs unchanged on Windows,
macOS and Linux.

CONTRACT: every run prints exactly ONE line.
    OK:<payload>       payload is a raw string or compact JSON
    ERR:<code>:<msg>   a failed step; <code> is stable and machine readable
The process exits 0 by default and 1 on ERR only when --strict-exit is given,
so that "the prefix is the verdict" stays true no matter how this is called.

Commands
    info                        GET /json/version (browser, protocol, ws endpoint)
    targets                     list debug targets as JSON
    eval -e <js>                Runtime.evaluate, prints the value
    click -s <css>              scroll into view, hit-test, real mouse sequence
    type -s <css> -t <text>     focus, optional clear, insertText, optional Enter
    key -k <name>               dispatch a keystroke (Enter/Escape/Tab/.../a)
    wait -s <css> | -e <js>     poll in-page until truthy (or --gone)
    text -s <css>               innerText of an element
    html -s <css>               outerHTML of an element
    shot -o <file>              Page.captureScreenshot to a PNG file
    nav -u <url>                Page.navigate, then wait for readyState complete
    open -u <url>               PUT /json/new, prints the new target id
    close --target-id <id>      GET /json/close/<id>

Endpoint / target selection
    --port <n>        CDP HTTP port. Omit to probe 9333,9222,9229,9444,9223,8315.
    --url-match <s>   pick the target whose url contains <s>. Do this whenever
                      the endpoint has more than one page target.
    --target-id <id>  pin one exact target id.
    --target-type <t> default 'page'.
    --first           accept the first match instead of failing on ambiguity.
    --ws-url <ws>     connect straight to a websocket endpoint (browser-level).
  With several matching page targets and no pin, the script refuses to guess:
  /json reorders when tabs open, so "the first page" is not a stable identity.

Examples
    python3 cdp.py targets
    python3 cdp.py eval -e "document.title"
    python3 cdp.py eval -e "JSON.stringify({n:document.querySelectorAll('button').length})"
    python3 cdp.py click -s "button.primary" --text "Submit"
    python3 cdp.py type -s "textarea" -t "hello" --submit
    python3 cdp.py wait -s ".result" --timeout 15000
    python3 cdp.py shot -o ./ui.png --full-page
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Keep the skill directory free of __pycache__ build artifacts; the two
# sibling modules below are imported after this takes effect.
sys.dont_write_bytecode = True

import cdpai
import cdpui
from cdpui import Driver, bound, format_eval_value
from cdpws import (DEFAULT_PORTS, CdpError, compact, emit_err, emit_ok, get_targets,
                   http_json, http_text)

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_info(drv: Driver):
    data = http_json(drv.port, "/json/version", timeout=5.0)
    emit_ok(compact({"port": drv.port, "browser": data.get("Browser"),
                     "protocol": data.get("Protocol-Version"),
                     "ws": data.get("webSocketDebuggerUrl")}))


def cmd_targets(drv: Driver):
    rows = get_targets(drv.port)
    if drv.args.target_type_explicit:
        rows = [t for t in rows if t.get("type") == drv.args.target_type]
    if drv.args.url_match:
        rows = [t for t in rows if drv.args.url_match in (t.get("url") or "")]
    listed = [{"id": t.get("id"), "type": t.get("type"),
               "title": t.get("title"), "url": t.get("url")} for t in rows]
    emit_ok(compact({"port": drv.port, "count": len(listed), "targets": listed}))


def cmd_open(drv: Driver):
    if not drv.args.url:
        raise CdpError("missing-arg", "open requires --url")
    created = http_json(drv.port, "/json/new?" + drv.args.url, method="PUT", timeout=10.0)
    emit_ok(compact({"id": created.get("id"), "url": created.get("url")}))


def cmd_close(drv: Driver):
    if not drv.args.target_id:
        raise CdpError("missing-arg", "close requires --target-id")
    reply = http_text(drv.port, "/json/close/" + urllib.parse.quote(drv.args.target_id), timeout=10.0)
    emit_ok(compact({"closed": drv.args.target_id, "reply": reply.strip()}))


def cmd_eval(drv: Driver):
    js = drv.args.expression
    if drv.args.expression_file:
        if not os.path.isfile(drv.args.expression_file):
            raise CdpError("missing-file", "no such file: %s" % drv.args.expression_file)
        with open(drv.args.expression_file, "r", encoding="utf-8") as fh:
            js = fh.read()
    if not js:
        raise CdpError("missing-arg", "eval requires -e/--expression or -E/--expression-file")
    emit_ok(bound(format_eval_value(drv.evaluate(js)), drv.args.max_chars))


def cmd_click(drv: Driver):
    if not drv.args.selector:
        raise CdpError("missing-arg", "click requires -s/--selector")
    info = drv.locate(drv.args.selector, drv.args.text, drv.args.index)
    if not info.get("ok"):
        raise CdpError("no-match", "selector='%s' text='%s' reason=%s total=%s"
                       % (drv.args.selector, drv.args.text, info.get("reason"), info.get("total")))
    if not info.get("inside") and not drv.args.force:
        raise CdpError("occluded", "element center x=%s y=%s is covered by '%s'; re-target or pass --force"
                       % (info["x"], info["y"], info.get("hit")))
    drv.mouse_click(info["x"], info["y"])
    emit_ok(compact({"x": info["x"], "y": info["y"], "w": info["w"], "h": info["h"],
                     "matches": info["total"], "visible": info["visible"], "deep": info["deep"],
                     "tag": info["tag"], "text": info["text"]}))


def cmd_type(drv: Driver):
    if not drv.args.selector:
        raise CdpError("missing-arg", "type requires -s/--selector")
    if not drv.args.text:
        raise CdpError("missing-arg", "type requires -t/--text")
    info = drv.locate(drv.args.selector, "", drv.args.index)
    if not info.get("ok"):
        raise CdpError("no-match", "selector='%s' reason=%s" % (drv.args.selector, info.get("reason")))
    drv.mouse_click(info["x"], info["y"])
    if drv.args.clear:
        clear_js = (
            "(() => { const n = document.querySelector(%s); if (!n) return 'missing';"
            " if (typeof n.setSelectionRange === 'function' && typeof n.value === 'string')"
            " { n.focus(); n.setSelectionRange(0, n.value.length); return 'range'; }"
            " const r = document.createRange(); r.selectNodeContents(n);"
            " const s = getSelection(); s.removeAllRanges(); s.addRange(r); return 'range-node'; })()"
            % json.dumps(drv.args.selector)
        )
        drv.evaluate(clear_js)
    # insertText drives the browser's own editing pipeline, so controlled
    # components receive a real `input` event. Assigning node.value does not.
    drv.connect().request("Input.insertText", {"text": drv.args.text}, budget_ms=drv.args.timeout)
    if drv.args.submit:
        drv.keystroke("Enter")
    time.sleep(0.12)
    read_js = (
        "(() => { const n = document.querySelector(%s); if (!n) return '__missing__';"
        " if (typeof n.value === 'string') return n.value;"
        " return (n.innerText || n.textContent || ''); })()" % json.dumps(drv.args.selector)
    )
    value = format_eval_value(drv.evaluate(read_js))
    emit_ok(compact({"selector": drv.args.selector, "submitted": bool(drv.args.submit),
                     "cleared": bool(drv.args.clear), "value": bound(value, drv.args.max_chars)}))


def cmd_key(drv: Driver):
    if drv.args.selector:
        info = drv.locate(drv.args.selector, drv.args.text, drv.args.index)
        if not info.get("ok"):
            raise CdpError("no-match", "selector='%s' reason=%s" % (drv.args.selector, info.get("reason")))
        drv.mouse_click(info["x"], info["y"])
    drv.keystroke(drv.args.key)
    emit_ok(compact({"key": drv.args.key, "modifiers": drv.args.modifiers,
                     "focused": bool(drv.args.selector)}))


def cmd_wait(drv: Driver):
    if not drv.args.selector and not drv.args.expression:
        raise CdpError("missing-arg", "wait requires -s/--selector or -e/--expression")
    if drv.args.selector:
        probe = "!!document.querySelector(%s)" % json.dumps(drv.args.selector)
    else:
        probe = "!!(%s)" % drv.args.expression
    if drv.args.gone:
        probe = "!(%s)" % probe
    # Poll in-page: one round trip instead of one per tick.
    wait_js = (
        "(async () => { const start = Date.now(); const deadline = start + %d;"
        " for (;;) { let ok = false; try { ok = %s; } catch (e) { ok = false; }"
        " if (ok) return JSON.stringify({ ok: true, waitedMs: Date.now() - start });"
        " if (Date.now() > deadline) return JSON.stringify({ ok: false, waitedMs: Date.now() - start });"
        " await new Promise(r => setTimeout(r, %d)); } })()"
        % (drv.args.timeout, probe, drv.args.poll_ms)
    )
    res = drv.evaluate(wait_js, budget_ms=drv.args.timeout + 3000)
    if res.get("exceptionDetails"):
        raise CdpError("wait-exception", str(res["exceptionDetails"].get("text")))
    info = json.loads(res["result"]["value"])
    if not info.get("ok"):
        what = ("selector='%s'" % drv.args.selector) if drv.args.selector else ("expression='%s'" % drv.args.expression)
        want = "absent" if drv.args.gone else "present"
        raise CdpError("timeout", "condition never became %s within %sms (%s)"
                       % (want, info.get("waitedMs"), what))
    emit_ok(compact({"waitedMs": info.get("waitedMs"), "selector": drv.args.selector,
                     "gone": bool(drv.args.gone)}))


def _text_or_html(drv: Driver, attribute: str):
    if not drv.args.selector:
        raise CdpError("missing-arg", "%s requires -s/--selector" % attribute)
    expr = "(n.innerText || n.textContent) || ''" if attribute == "text" else "n.outerHTML || ''"
    js = ("(() => { const n = document.querySelector(%s); if (!n) return null;"
          " return (%s).slice(0, %d); })()" % (json.dumps(drv.args.selector), expr, drv.args.max_chars))
    res = drv.evaluate(js)
    if res.get("exceptionDetails"):
        raise CdpError("eval-exception", str(res["exceptionDetails"].get("text")))
    inner = res.get("result") or {}
    if inner.get("type") == "object" and inner.get("value") is None:
        raise CdpError("no-match", "selector='%s' matched nothing" % drv.args.selector)
    emit_ok(format_eval_value(res))


def cmd_text(drv: Driver):
    _text_or_html(drv, "text")


def cmd_html(drv: Driver):
    _text_or_html(drv, "html")


def cmd_shot(drv: Driver):
    if not drv.args.out:
        raise CdpError("missing-arg", "shot requires -o/--out")
    if drv.args.width > 0 and drv.args.height > 0:
        drv.connect().request("Emulation.setDeviceMetricsOverride", {
            "width": drv.args.width, "height": drv.args.height,
            "deviceScaleFactor": 1, "mobile": False,
        }, budget_ms=drv.args.timeout)
    params = {"format": "png"}
    if drv.args.full_page:
        params["captureBeyondViewport"] = True
    res = drv.connect().request("Page.captureScreenshot", params,
                                budget_ms=max(drv.args.timeout, 60000))
    data = res.get("data")
    if not data:
        raise CdpError("shot-empty", "captureScreenshot returned no data "
                                     "(window minimized or not composited?)")
    out_path = os.path.abspath(os.path.expanduser(drv.args.out))
    parent = os.path.dirname(out_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    payload = base64.b64decode(data)
    with open(out_path, "wb") as fh:
        fh.write(payload)
    emit_ok(compact({"path": out_path, "bytes": len(payload), "fullPage": bool(drv.args.full_page)}))


def cmd_nav(drv: Driver):
    if not drv.args.url:
        raise CdpError("missing-arg", "nav requires --url")
    drv.connect().request("Page.enable", {}, budget_ms=drv.args.timeout)
    res = drv.connect().request("Page.navigate", {"url": drv.args.url}, budget_ms=drv.args.timeout)
    if res.get("errorText"):
        raise CdpError("nav-failed", "%s for %s" % (res["errorText"], drv.args.url))
    # The document is replaced, so readiness must be re-read on the new one.
    wait_js = (
        "(async () => { const start = Date.now(); const deadline = start + %d;"
        " for (;;) { if (document.readyState === 'complete')"
        " return JSON.stringify({ ok: true, waitedMs: Date.now() - start, url: location.href });"
        " if (Date.now() > deadline) return JSON.stringify({ ok: false, waitedMs: Date.now() - start, url: location.href });"
        " await new Promise(r => setTimeout(r, %d)); } })()" % (drv.args.timeout, drv.args.poll_ms)
    )
    ready = drv.evaluate(wait_js, budget_ms=drv.args.timeout + 3000)
    if ready.get("exceptionDetails"):
        raise CdpError("nav-failed", str(ready["exceptionDetails"].get("text")))
    info = json.loads(ready["result"]["value"])
    if not info.get("ok"):
        raise CdpError("nav-timeout", "readyState never reached complete within %sms (url=%s)"
                       % (info.get("waitedMs"), info.get("url")))
    emit_ok(compact({"url": info.get("url"), "waitedMs": info.get("waitedMs")}))


def _laya_config(args) -> dict:
    return cdpai.resolve_config(getattr(args, "laya_url", ""),
                                getattr(args, "laya_key", ""),
                                getattr(args, "laya_timeout", 0.0))


def emit_laya_health(args) -> None:
    """Standalone: checking the decision service must not require a browser."""
    config = _laya_config(args)
    data = cdpai.health(config)
    emit_ok(compact({
        "baseUrl": config["base_url"],
        "keyConfigured": bool(config["api_key"]),
        "configuredFrom": config["origin"],
        "status": data.get("status"),
        "device": data.get("device"),
        "loaded": data.get("loaded"),
    }))


def cmd_pick(drv: Driver):
    """Choose one element out of a candidate pool using a semantic decision."""
    if not drv.args.intent:
        raise CdpError("missing-arg", "pick requires --intent (what you are trying to do)")
    config = _laya_config(drv.args)

    pool = drv.candidates(drv.args.selector, drv.args.limit)
    if not pool.get("ok"):
        raise CdpError("no-match", "selector='%s' reason=%s" % (drv.args.selector, pool.get("reason")))
    if not pool.get("rows"):
        raise CdpError("no-match", "selector='%s' matched nothing" % drv.args.selector)

    rows = pool["rows"]
    labels = cdpui.candidate_labels(rows)
    criteria = {labels[i]: labels[i] for i in range(len(rows))}
    index_by_label = {labels[i]: i for i in range(len(rows))}

    lead = ""
    if drv.args.context:
        lead = drv.args.context.rstrip() + "\n"
    state = ("The user wants to: %s\n"
             "%s"
             "Candidate elements on the page (%d described of %d matches):\n%s"
             % (drv.args.intent, lead, len(rows), pool.get("total", len(rows)),
                "\n".join("- " + label for label in labels)))

    questions = {"target": cdpai.choice_question(
        "Which single candidate element should be acted on to accomplish the user's goal?",
        criteria)}
    result = cdpai.ask(config, state, questions)
    answer = (result.get("answers") or {}).get("target") or {}
    chosen = answer.get("choice")
    index = index_by_label.get(chosen) if isinstance(chosen, str) else None
    if index is None:
        raise CdpError("pick-undecided",
                       "the model returned %r, which is not one of the offered candidates" % (chosen,))

    probabilities = answer.get("probabilities") or {}
    ranked = sorted((float(v) for v in probabilities.values()), reverse=True)
    margin = round(ranked[0] - ranked[1], 4) if len(ranked) > 1 else round(ranked[0], 4) if ranked else 0.0
    probability = round(float(probabilities.get(chosen, cdpai.answer_probability(answer))), 4)

    # Measured on a live CPU deployment, runner-up margins on real pages landed
    # between 0.03 and 0.19, and small prompt changes flipped the winner. A pick
    # with no daylight between the top two is a coin flip wearing a confidence
    # number, so refuse by default instead of silently clicking the wrong thing.
    if margin < drv.args.min_margin:
        raise CdpError(
            "pick-low-margin",
            "top candidate %r beat the runner-up by only %.4f (below --min-margin %.4f); "
            "narrow -s, add --context, or pass --min-margin 0 to accept it. "
            "probabilities=%s" % (chosen, margin, drv.args.min_margin, compact(probabilities)),
        )
    if probability < drv.args.min_probability:
        raise CdpError("pick-low-confidence",
                       "best candidate %r scored %.4f, below --min-probability %.4f"
                       % (chosen, probability, drv.args.min_probability))

    row = rows[index]
    payload = {
        "chosen": chosen,
        "probability": probability,
        "runnerUpMargin": margin,
        "probabilities": probabilities,
        "model": result.get("model"),
        "candidatesDescribed": len(rows),
        "candidatesMatched": pool.get("total"),
        "shadowFallback": bool(pool.get("deep")),
        "truncated": bool(pool.get("capped")),
        "element": cdpui.describe_candidate(row),
    }

    if drv.args.click:
        selector = drv.args.selector
        info = drv.locate(selector, "", index)
        if not info.get("ok"):
            raise CdpError("no-match", "chosen candidate no longer resolves (index=%d)" % index)
        if not info.get("inside") and not drv.args.force:
            raise CdpError("occluded", "chosen element x=%s y=%s is covered by '%s'; resolve the "
                                       "overlay or pass --force" % (info["x"], info["y"], info.get("hit")))
        drv.mouse_click(info["x"], info["y"])
        payload["clicked"] = {"x": info["x"], "y": info["y"], "tag": info["tag"]}

    emit_ok(compact(payload))


def cmd_judge(drv: Driver):
    """Ask a calibrated question about the current page state."""
    if not drv.args.question:
        raise CdpError("missing-arg", "judge requires --question")
    config = _laya_config(drv.args)

    context_js = (
        "(() => { const n = document.querySelector(%s);"
        " if (!n) return null;"
        " return ((n.innerText || n.textContent || '')).replace(/\\s+/g, ' ').trim().slice(0, %d); })()"
        % (json.dumps(drv.args.context_selector), drv.args.max_chars)
    )
    snapshot = drv.evaluate(context_js)
    if snapshot.get("exceptionDetails"):
        raise CdpError("judge-context", str(snapshot["exceptionDetails"].get("text")))
    inner = snapshot.get("result") or {}
    if inner.get("type") == "object" and inner.get("value") is None:
        raise CdpError("no-match", "context selector '%s' matched nothing" % drv.args.context_selector)
    body = inner.get("value") or ""

    state = body
    if drv.args.with_url:
        meta = drv.evaluate("JSON.stringify({title: document.title, url: location.href})")
        state = "Page: %s\n%s" % (cdpui.format_eval_value(meta), body)

    kind = drv.args.judge_type
    if kind == "noul":
        question = cdpai.noul_question(drv.args.question)
    elif kind == "score":
        scale = [item.strip() for item in drv.args.criteria.split(",") if item.strip()]
        if len(scale) < 2:
            raise CdpError("missing-arg", "score needs --criteria with at least 2 comma-separated steps")
        question = cdpai.score_question(drv.args.question, scale)
    else:
        criteria = {}
        for item in drv.args.criteria.split(","):
            if "=" not in item:
                raise CdpError("missing-arg", "choice needs --criteria as key=description,key=description")
            label, _, description = item.partition("=")
            if label.strip():
                criteria[label.strip()] = description.strip()
        if len(criteria) < 2:
            raise CdpError("missing-arg", "choice needs at least 2 --criteria entries")
        question = cdpai.choice_question(drv.args.question, criteria)

    result = cdpai.ask(config, state, {"verdict": question})
    answer = (result.get("answers") or {}).get("verdict") or {}
    probability = cdpai.answer_probability(answer)
    if probability < drv.args.min_confidence:
        raise CdpError("judge-low-confidence",
                       "verdict scored %.4f, below --min-confidence %.4f" % (probability, drv.args.min_confidence))

    emit_ok(compact({
        "question": drv.args.question,
        "type": kind,
        "verdict": answer.get("choice") if kind == "choice" else (
            answer.get("score") if kind == "score" else answer.get("noul")),
        "probability": round(probability, 4),
        "answer": answer,
        "model": result.get("model"),
        "routing": (result.get("routing") or {}).get("model"),
        "stateChars": len(state),
    }))


COMMANDS = {
    "info": cmd_info, "targets": cmd_targets, "eval": cmd_eval, "click": cmd_click,
    "type": cmd_type, "key": cmd_key, "wait": cmd_wait, "text": cmd_text,
    "html": cmd_html, "shot": cmd_shot, "nav": cmd_nav, "open": cmd_open, "close": cmd_close,
    "pick": cmd_pick, "judge": cmd_judge,
}

# Commands that need no browser target at all, so a missing page is not fatal.
NO_TARGET_COMMANDS = {"laya-health"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        emit_err("bad-args", "%s (run --help for usage)" % message)
        raise SystemExit(0)


def build_parser() -> _Parser:
    parser = _Parser(prog="cdp.py", description="One-shot Chrome DevTools Protocol driver.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--port", type=int, default=0,
                        help="CDP HTTP port; omit to probe %s" % ",".join(str(p) for p in DEFAULT_PORTS))
    common.add_argument("--url-match", default="", help="pick the target whose url contains this")
    common.add_argument("--target-id", default="", help="pin one exact target id")
    common.add_argument("--target-type", default="page", help="target type (default: page)")
    common.add_argument("--first", action="store_true",
                        help="accept the first match instead of failing on ambiguity")
    common.add_argument("--ws-url", default="", help="connect straight to a websocket endpoint")
    common.add_argument("--timeout", type=int, default=30000, help="budget in ms (default 30000)")
    common.add_argument("--poll-ms", type=int, default=200, help="polling interval in ms")
    common.add_argument("--strict-exit", action="store_true", help="exit 1 on ERR instead of 0")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info", parents=[common])
    sub.add_parser("targets", parents=[common])

    p = sub.add_parser("eval", parents=[common])
    p.add_argument("-e", "--expression", default="")
    p.add_argument("-E", "--expression-file", default="")
    p.add_argument("--user-gesture", action="store_true")
    p.add_argument("--no-await", action="store_true")
    p.add_argument("--max-chars", type=int, default=4000)

    p = sub.add_parser("click", parents=[common])
    p.add_argument("-s", "--selector", default="")
    p.add_argument("--text", default="")
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("type", parents=[common])
    p.add_argument("-s", "--selector", default="")
    p.add_argument("-t", "--text", default="")
    p.add_argument("--clear", action="store_true")
    p.add_argument("--submit", action="store_true")
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--max-chars", type=int, default=4000)

    p = sub.add_parser("key", parents=[common])
    p.add_argument("-k", "--key", default="Enter")
    p.add_argument("-s", "--selector", default="")
    p.add_argument("--text", default="")
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--modifiers", type=int, default=0)

    p = sub.add_parser("wait", parents=[common])
    p.add_argument("-s", "--selector", default="")
    p.add_argument("-e", "--expression", default="")
    p.add_argument("--gone", action="store_true")

    for name in ("text", "html"):
        p = sub.add_parser(name, parents=[common])
        p.add_argument("-s", "--selector", default="")
        p.add_argument("--max-chars", type=int, default=4000)

    p = sub.add_parser("shot", parents=[common])
    p.add_argument("-o", "--out", default="")
    p.add_argument("--full-page", action="store_true")
    p.add_argument("--width", type=int, default=0)
    p.add_argument("--height", type=int, default=0)

    p = sub.add_parser("nav", parents=[common])
    p.add_argument("-u", "--url", default="")

    p = sub.add_parser("open", parents=[common])
    p.add_argument("-u", "--url", default="")

    p = sub.add_parser("close", parents=[common])

    # -- Laya-backed semantic commands (see cdpai.py) ----------------------
    laya = argparse.ArgumentParser(add_help=False)
    laya.add_argument("--laya-url", default="", help="Laya base URL; else env or config file")
    laya.add_argument("--laya-key", default="", help="Laya bearer token, if the server needs one")
    laya.add_argument("--laya-timeout", type=float, default=0.0, help="Laya request budget in seconds")

    sub.add_parser("laya-health", parents=[common, laya])

    p = sub.add_parser("pick", parents=[common, laya])
    p.add_argument("-s", "--selector", default="button, a, input, [role=button]",
                   help="candidate pool (default: button, a, input, [role=button])")
    p.add_argument("--intent", default="", help="what you are trying to accomplish, in plain language")
    p.add_argument("--limit", type=int, default=40, help="max candidates to describe (default 40)")
    p.add_argument("--min-probability", type=float, default=0.0,
                   help="fail instead of answering when the winning probability is below this")
    p.add_argument("--min-margin", type=float, default=0.10,
                   help="fail when the winner's lead over the runner-up is below this "
                        "(default 0.10; pass 0 to accept a near tie)")
    p.add_argument("--click", action="store_true", help="click the chosen element right away")
    p.add_argument("--force", action="store_true", help="with --click, click even if occluded")
    p.add_argument("--context", default="", help="extra page context to send along")

    p = sub.add_parser("judge", parents=[common, laya])
    p.add_argument("--question", default="", help="the decision you want answered")
    p.add_argument("--type", dest="judge_type", default="noul",
                   choices=("noul", "score", "choice"))
    p.add_argument("--criteria", default="",
                   help="score: comma-separated ordered scale; choice: comma-separated key=description")
    p.add_argument("--context-selector", default="body", help="element whose text is the state (default body)")
    p.add_argument("--max-chars", type=int, default=1500, help="cap on the state text sent")
    p.add_argument("--with-url", action="store_true", help="prepend the page title and URL to the state")
    p.add_argument("--min-confidence", type=float, default=0.0,
                   help="fail instead of answering when the winning probability is below this")

    return parser


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    # `targets` should list everything unless the caller really filtered.
    args.target_type_explicit = any(a == "--target-type" or a.startswith("--target-type=")
                                    for a in argv)
    for attr, default in (("selector", ""), ("text", ""), ("index", 0), ("force", False),
                          ("expression", ""), ("expression_file", ""), ("user_gesture", False),
                          ("no_await", False), ("max_chars", 4000), ("clear", False),
                          ("submit", False), ("key", "Enter"), ("modifiers", 0), ("gone", False),
                          ("out", ""), ("full_page", False), ("width", 0), ("height", 0),
                          ("url", ""), ("target_id", "")):
        if not hasattr(args, attr):
            setattr(args, attr, default)

    drv = None
    try:
        if args.command in NO_TARGET_COMMANDS:
            emit_laya_health(args)
        else:
            drv = Driver(args)
            COMMANDS[args.command](drv)
    except CdpError as exc:
        emit_err(exc.code, exc.message)
        return 1 if args.strict_exit else 0
    except urllib.error.URLError as exc:
        emit_err("http-failed", str(exc))
        return 1 if args.strict_exit else 0
    except KeyboardInterrupt:
        emit_err("interrupted", "aborted by user")
        return 1 if args.strict_exit else 0
    except Exception as exc:  # never leak a traceback where a one-liner is promised
        emit_err("exception", "%s: %s" % (type(exc).__name__, exc))
        return 1 if args.strict_exit else 0
    finally:
        if drv is not None and drv.sock:
            drv.sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
