"""Page-level operations for cdp.py: locate, click, type, evaluate.

Sits between the transport layer (cdpws.py) and the CLI (cdp.py). Imported by
cdp.py; not meant to be run directly.
"""

from __future__ import annotations

import json
import time

from cdpws import CdpError, CdpSocket, compact, resolve_port, select_target
# ---------------------------------------------------------------------------
# Shared in-page locator. Prefers visible nodes, falls back to shadow DOM,
# exposes an occlusion verdict so a click never silently lands on an overlay.
# ---------------------------------------------------------------------------
KEY_TABLE = {
    "Enter": (13, "Enter", "\r"),
    "Escape": (27, "Escape", ""),
    "Tab": (9, "Tab", ""),
    "Backspace": (8, "Backspace", ""),
    "Delete": (46, "Delete", ""),
    "Space": (32, "Space", " "),
    "ArrowUp": (38, "ArrowUp", ""),
    "ArrowDown": (40, "ArrowDown", ""),
    "ArrowLeft": (37, "ArrowLeft", ""),
    "ArrowRight": (39, "ArrowRight", ""),
    "Home": (36, "Home", ""),
    "End": (35, "End", ""),
    "PageUp": (33, "PageUp", ""),
    "PageDown": (34, "PageDown", ""),
    "F5": (116, "F5", ""),
    "F12": (123, "F12", ""),
}

LOCATOR_JS = r"""
(() => {
  const SEL = __SEL__;
  const TEXT = __TEXT__;
  const INDEX = __INDEX__;
  const describe = (n) => {
    if (!n) return null;
    const id = n.id ? ('#' + n.id) : '';
    let cls = '';
    if (typeof n.className === 'string' && n.className.trim()) {
      cls = '.' + n.className.trim().split(/\s+/).slice(0, 3).join('.');
    }
    const title = n.getAttribute ? n.getAttribute('title') : '';
    return n.tagName.toLowerCase() + id + cls + (title ? ('[title="' + title + '"]') : '');
  };
  const visible = (n) => {
    const r = n.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) return false;
    const s = getComputedStyle(n);
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const deepAll = () => {
    const out = [];
    const seen = new Set();
    const walk = (root) => {
      let list = [];
      try { list = Array.from(root.querySelectorAll(SEL)); } catch (e) { return; }
      for (const n of list) { if (!seen.has(n)) { seen.add(n); out.push(n); } }
      let all = [];
      try { all = root.querySelectorAll('*'); } catch (e) { return; }
      for (const n of all) { if (n.shadowRoot) walk(n.shadowRoot); }
    };
    walk(document);
    return out;
  };
  let direct = [];
  try { direct = Array.from(document.querySelectorAll(SEL)); } catch (e) {
    return JSON.stringify({ ok: false, reason: 'bad-selector' });
  }
  let nodes = direct;
  let deep = false;
  if (nodes.length === 0) { nodes = deepAll(); deep = nodes.length > 0; }
  if (TEXT) nodes = nodes.filter((n) => ((n.innerText || n.textContent || '')).indexOf(TEXT) >= 0);
  const vis = nodes.filter(visible);
  const pool = vis.length ? vis : nodes;
  const node = pool[INDEX];
  if (!node) {
    return JSON.stringify({ ok: false, reason: 'no-match', total: nodes.length, visible: vis.length });
  }
  node.scrollIntoView({ block: 'center', inline: 'center' });
  const r = node.getBoundingClientRect();
  const x = Math.round(r.left + r.width / 2);
  const y = Math.round(r.top + r.height / 2);
  // Hit-test inside the node's OWN root: document.elementFromPoint retargets to
  // the shadow host, which would report a false occlusion for shadow content.
  const ownerRoot = node.getRootNode();
  const hitsInRoot = (ownerRoot && typeof ownerRoot.elementFromPoint === 'function');
  const hit = hitsInRoot ? ownerRoot.elementFromPoint(x, y) : document.elementFromPoint(x, y);
  const docHit = (ownerRoot === document) ? hit : document.elementFromPoint(x, y);
  const composedContains = (ancestor, other) => {
    let cur = other;
    while (cur) {
      if (cur === ancestor) return true;
      cur = cur.parentNode || cur.host || null;
    }
    return false;
  };
  return JSON.stringify({
    ok: true,
    x: x, y: y,
    w: Math.round(r.width), h: Math.round(r.height),
    total: nodes.length, visible: vis.length, deep: deep,
    tag: describe(node), hit: describe(hit), docHit: describe(docHit),
    inside: composedContains(node, hit),
    text: (node.innerText || node.textContent || '').slice(0, 80),
    value: (typeof node.value === 'string') ? node.value.slice(0, 200) : null
  });
})()
"""


class Driver:
    def __init__(self, args):
        self.args = args
        self.port = resolve_port(args.port) if (args.port or args.ws_url) else resolve_port(0)
        self.sock = None

    # -- plumbing ----------------------------------------------------------
    def connect(self):
        if self.sock:
            return self.sock
        ws_url = self.args.ws_url
        if not ws_url:
            target = None
            for _ in range(10):
                target = select_target(self.port, self.args.target_type, self.args.url_match,
                                       self.args.target_id, self.args.first)
                if target:
                    break
                time.sleep(0.25)
            if not target:
                raise CdpError("no-target", "no target with type=%s urlMatch='%s' on port %d"
                               % (self.args.target_type, self.args.url_match, self.port))
            ws_url = target.get("webSocketDebuggerUrl")
            if not ws_url:
                raise CdpError("no-target", "target %s exposes no webSocketDebuggerUrl" % target.get("id"))
        self.sock = CdpSocket(ws_url, self.args.timeout / 1000.0)
        return self.sock

    def evaluate(self, expression: str, budget_ms: int = 0):
        params = {"expression": expression, "returnByValue": True}
        if not self.args.no_await:
            params["awaitPromise"] = True
        if self.args.user_gesture:
            params["userGesture"] = True
        budget = budget_ms or self.args.timeout
        if budget > 0:
            params["timeout"] = budget
        return self.connect().request("Runtime.evaluate", params, budget_ms=budget + 5000)

    def locate(self, selector: str, text: str = "", index: int = 0):
        js = (LOCATOR_JS
              .replace("__SEL__", json.dumps(selector))
              .replace("__TEXT__", json.dumps(text or ""))
              .replace("__INDEX__", str(int(index))))
        res = self.evaluate(js)
        if res.get("exceptionDetails"):
            raise CdpError("locate-failed", str(res["exceptionDetails"].get("text")))
        return json.loads(res["result"]["value"])

    def mouse_click(self, x: int, y: int):
        base = {"x": x, "y": y, "button": "left", "clickCount": 1}
        for kind, buttons in (("mouseMoved", 0), ("mousePressed", 1),
                              ("mouseReleased", 0), ("mouseMoved", 0)):
            params = dict(base)
            params["type"] = kind
            params["buttons"] = buttons
            self.connect().request("Input.dispatchMouseEvent", params, budget_ms=self.args.timeout)

    def keystroke(self, name: str):
        if name in KEY_TABLE:
            vk, code, text = KEY_TABLE[name]
        elif len(name) == 1:
            vk = ord(name.upper())
            code = "Key" + name.upper()
            text = name
        else:
            raise CdpError("bad-key", "unsupported key name '%s'" % name)
        for kind, payload in (("keyDown", text), ("keyUp", "")):
            self.connect().request("Input.dispatchKeyEvent", {
                "type": kind, "key": name, "code": code, "text": payload,
                "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
                "modifiers": self.args.modifiers,
            }, budget_ms=self.args.timeout)

    def candidates(self, selector: str, limit: int = 40):
        """Describe the elements a semantic picker would choose between.

        Only visible nodes are described when any exist, because a page almost
        always carries hidden duplicates and feeding those to a decision model
        manufactures ambiguity that the user never sees on screen.
        """
        js = (CANDIDATES_JS
              .replace("__SEL__", json.dumps(selector))
              .replace("__LIMIT__", str(int(limit))))
        res = self.evaluate(js)
        if res.get("exceptionDetails"):
            raise CdpError("candidates-failed", str(res["exceptionDetails"].get("text")))
        return json.loads(res["result"]["value"])


CANDIDATES_JS = r"""
(() => {
  const SEL = __SEL__;
  const LIMIT = __LIMIT__;
  const visible = (n) => {
    const r = n.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) return false;
    const s = getComputedStyle(n);
    return s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const squeeze = (s) => (s || '').replace(/\s+/g, ' ').trim();
  let direct = [];
  try { direct = Array.from(document.querySelectorAll(SEL)); } catch (e) {
    return JSON.stringify({ ok: false, reason: 'bad-selector' });
  }
  let nodes = direct;
  let deep = false;
  if (nodes.length === 0) {
    const out = [];
    const walk = (root) => {
      let list = [];
      try { list = Array.from(root.querySelectorAll(SEL)); } catch (e) { return; }
      for (const n of list) out.push(n);
      let all = [];
      try { all = root.querySelectorAll('*'); } catch (e) { return; }
      for (const n of all) { if (n.shadowRoot) walk(n.shadowRoot); }
    };
    walk(document);
    nodes = out;
    deep = nodes.length > 0;
  }
  const vis = nodes.filter(visible);
  const pool = vis.length ? vis : nodes;
  const capped = pool.length > LIMIT;
  const rows = pool.slice(0, LIMIT).map((n, i) => ({
    i: i,
    tag: n.tagName.toLowerCase(),
    id: n.id || '',
    cls: squeeze(typeof n.className === 'string' ? n.className : '').split(' ').slice(0, 2).join(' '),
    role: n.getAttribute('role') || '',
    aria: squeeze(n.getAttribute('aria-label')),
    name: n.getAttribute('name') || '',
    title: squeeze(n.getAttribute('title')),
    kind: n.getAttribute('type') || '',
    ph: squeeze(n.getAttribute('placeholder')),
    disabled: !!n.disabled,
    visible: visible(n),
    text: squeeze(n.innerText || n.textContent || '').slice(0, 60)
  }));
  return JSON.stringify({
    ok: true, total: nodes.length, visible: vis.length, deep: deep,
    capped: capped, described: rows.length, rows: rows
  });
})()
"""


def describe_candidate(row: dict) -> str:
    """A compact, human-readable label for one candidate element.

    This doubles as the `criteria` key handed to the decision model, which is
    deliberate: measured on a live deployment, reasoning over a readable
    description beat reasoning over a synthetic key ("0|点击计数") by a wide
    margin, because a synthetic key injects meaningless tokens into the exact
    sequence the model scores. Keep it a sentence a person could act on.
    """
    parts = [row.get("tag") or "node"]
    if row.get("role"):
        parts.append("role=" + str(row["role"]))
    if row.get("id"):
        parts.append("#" + str(row["id"]))
    if row.get("cls"):
        parts.append("." + str(row["cls"]).replace(" ", "."))
    for field, prefix in (("kind", "type="), ("name", "name="), ("aria", "aria-label="),
                          ("title", "title="), ("ph", "placeholder=")):
        if row.get(field):
            parts.append(prefix + str(row[field]))
    if row.get("disabled"):
        parts.append("disabled")
    if not row.get("visible"):
        parts.append("not-visible")
    label = " ".join(parts)
    text = row.get("text") or ""
    if text:
        label += ' text="' + text + '"'
    return label


def candidate_labels(rows: list) -> list:
    """Descriptions, made unique only where they would otherwise collide."""
    labels = [describe_candidate(row) for row in rows]
    counts = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return [label if counts[label] == 1 else "%s #%d" % (label, i + 1)
            for i, label in enumerate(labels)]


def format_eval_value(res) -> str:
    if res.get("exceptionDetails"):
        details = res["exceptionDetails"]
        exc = details.get("exception") or {}
        raise CdpError("eval-exception", exc.get("description") or details.get("text") or "unknown")
    inner = res.get("result") or {}
    kind = inner.get("type")
    if kind == "string":
        return inner.get("value", "")
    if kind == "undefined":
        return "undefined"
    if "value" not in inner:
        return compact({"type": kind})
    return compact(inner.get("value"))


def bound(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "...[truncated]"

