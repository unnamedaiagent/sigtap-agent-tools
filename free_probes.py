#!/usr/bin/env python3
"""free_probes.py — probe every sigtap Outreach API route with CANONICAL params.

Zero dependencies (Python 3 stdlib). Exits 0 only if ALL routes answer correctly:
free previews return 200 + expected JSON fields; paid endpoints return
HTTP 402 with a decodable base64 `payment-required` header (x402 v2).

Run before and after ANY doc change: python3 free_probes.py
The same probes run as a GitHub Actions smoke test (.github/workflows/probes.yml).

Params are canonical per the live /openapi.json — do not use legacy names
(input=/symbol=); the API rejects them with HTTP 400.

2026-09-06 retry design (CI run 34006568195 post-mortem): the edge throws
~60s brownout windows at RANDOM routes (CI: hash/crypto-price/domain-age;
sandbox pass A: jwt-decode; pass B: deliverability 3x, then curl 0.04s on the
same route seconds later). Per-attempt timeout 20s x 3 covers single stalls;
failed routes are then RE-PROBED as a group after a 45s cool-down (up to 2
extra passes) to bridge a brownout window. Happy path unchanged (<1 min);
worst case ~15 min < 25-min job budget (timeout-minutes sized to worst case,
0743dd7).
"""
import base64
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

BASE = "https://sigtap-outreach-api.sigtap.workers.dev"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
TIMEOUT = 20       # per attempt; a healthy 402 challenge answers in <1s
ATTEMPTS = 3       # per route per pass
PASSES = 3         # 1 full + 2 retry passes for failed routes only
COOLDOWN_S = 45    # between passes; bridges ~60s edge brownout windows

# (path, query, required response fields) — free routes must return 200
FREE = [
    ("/score-preview", {"subject": "Quick question about outreach"}, ["score"]),
    ("/hash-preview", {"text": "hello"}, ["sha256", "crc32"]),
    ("/health", {}, ["ok"]),
]

# (label, path, query) — paid routes must return 402 + base64 payment-required
# header decoding to a JSON object with x402Version/scheme/amount/payTo.
PAID = [
    ("deliverability", "/deliverability", {"domain": "example.com"}),
    ("grade", "/grade", {"subject": "Quick question", "body": "Hello there, short test."}),
    ("template", "/template", {"persona": "founder", "offer": "outreach tools"}),
    ("hash", "/tools/hash", {"text": "hello"}),
    ("jwt-decode", "/tools/jwt-decode", {"token": "eyJhbGciOiJub25lIn0.eyJ0ZXN0IjoxfQ."}),
    ("uuid", "/tools/uuid", {"count": "2", "version": "v4"}),
    ("slug", "/tools/slug", {"text": "Hello World"}),
    ("json", "/tools/json", {"data": '{"a":1}', "mode": "flatten"}),
    ("regex", "/tools/regex", {"pattern": "\\d+", "text": "a1b22"}),
    ("crypto-price", "/tools/crypto-price", {"from": "BTC", "to": "USD"}),
    ("domain-age", "/tools/domain-age", {"domain": "example.com"}),
    ("weather", "/tools/weather", {"lat": "52.52", "lon": "13.41"}),
]


def _fetch_once(path, query):
    url = BASE + path
    if query:
        url += "?" + urlencode(query)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        # Keep the email.message.Message (NOT dict()): its .get() is
        # case-insensitive. The header arrives as PAYMENT-REQUIRED (upper)
        # over HTTP/1.1 and payment-required (lower) over HTTP/2.
        return e.code, e.headers, e.read()


def _transient_err(err):
    if isinstance(err, (socket.timeout, TimeoutError, ConnectionError, OSError)):
        return True  # socket.timeout subclasses OSError; covers URLError(reason)
    if isinstance(err, urllib.error.URLError):
        return isinstance(getattr(err, "reason", None), OSError)
    return False


def fetch(path, query):
    """Up to ATTEMPTS tries on transient conditions only (timeouts / 5xx).

    Sustained degradation (4xx, malformed challenge) surfaces immediately.
    """
    for attempt in range(1, ATTEMPTS + 1):
        try:
            status, headers, body = _fetch_once(path, query)
        except Exception as e:
            if attempt < ATTEMPTS and _transient_err(e):
                time.sleep(2)
                continue
            raise
        if status >= 500 and attempt < ATTEMPTS:
            time.sleep(2)
            continue
        return status, headers, body
    raise RuntimeError("unreachable")


def _check_free(path, query, fields):
    status, headers, body = fetch(path, query)
    data = json.loads(body)
    if status == 200 and all(f in data for f in fields):
        return True, f"OK  free  {path} ({status}, fields {fields})"
    return False, (f"FAIL free  {path}: status={status} "
                   f"fields_missing={[f for f in fields if f not in data]}")


def _check_paid(label, path, query):
    status, headers, body = fetch(path, query)
    pay = headers.get("payment-required") or headers.get("Payment-Required")
    if status != 402 or not pay:
        return False, f"FAIL paid {label}: status={status}, payment-required header missing"
    req_doc = json.loads(base64.b64decode(pay))
    # x402 v2: x402Version lives at the TOP level; per-route terms
    # (scheme/amount/payTo/network) live inside accepts[0].
    acc = (req_doc.get("accepts") or [{}])[0]
    if req_doc.get("x402Version") == 2 and acc.get("scheme") == "exact" \
            and str(acc.get("amount", "")).isdigit() and acc.get("payTo") \
            and acc.get("network") == "eip155:8453":
        usd = int(acc["amount"]) / 1e6
        return True, f"OK  paid  {label}: 402 x402v2 exact amount={acc['amount']} (${usd:.3f})"
    return False, f"FAIL paid {label}: unexpected payment-required shape: {req_doc}"


def run_pass(targets):
    """targets: list of (kind, args) tuples. Returns (lines, failed_targets)."""
    lines, failed = [], []
    for target in targets:
        kind, args = target
        try:
            ok, msg = _check_free(*args) if kind == "free" else _check_paid(*args)
        except Exception as e:
            ok, msg = False, f"FAIL {args[0]}: {e}"
        lines.append(msg)
        if not ok:
            failed.append(target)
    return lines, failed


def main():
    free_targets = [("free", (path, query, fields)) for path, query, fields in FREE]
    paid_targets = [("paid", (label, path, query)) for label, path, query in PAID]
    all_targets = free_targets + paid_targets

    print(f"Probing {BASE}")
    lines, failed = run_pass(all_targets)
    for line in lines:
        print("  " + line)

    for extra in range(2, PASSES + 1):
        if not failed:
            break
        print(f"\n  -- {len(failed)} route(s) failed; cool-down {COOLDOWN_S}s "
              f"then retry pass {extra}/{PASSES} (edge brownout windows measured "
              f"~60s, 2026-09-06) --")
        time.sleep(COOLDOWN_S)
        lines, failed = run_pass(failed)
        for line in lines:
            print("  " + line)

    total = len(all_targets)
    ok = total - len(failed)
    print(f"\nresult: {ok} ok, {len(failed)} failed of {total} (passes used: "
          f"{PASSES if failed else ''}{'all clear' if not failed else ''})")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
