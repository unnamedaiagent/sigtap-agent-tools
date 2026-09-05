#!/usr/bin/env python3
"""free_probes.py — probe every PitchPilot Outreach API route with CANONICAL params.

Zero dependencies (Python 3 stdlib). Exits 0 only if ALL routes answer correctly:
free previews return 200 + expected JSON fields; paid endpoints return
HTTP 402 with a decodable base64 `payment-required` header (x402 v2).

Run before and after ANY doc change: python3 free_probes.py
The same probes run as a GitHub Actions smoke test (.github/workflows/probes.yml).

Params are canonical per the live /openapi.json — do not use legacy names
(input=/symbol=); the API rejects them with HTTP 400.
"""
import base64
import json
import sys
import urllib.request
from urllib.parse import urlencode

BASE = "https://pitchpilot-outreach-api.pitchpilot-agents.workers.dev"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
TIMEOUT = 20

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


def fetch(path, query):
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


def main():
    ok = 0
    bad = 0
    print(f"Probing {BASE}")
    for path, query, fields in FREE:
        try:
            status, headers, body = fetch(path, query)
            data = json.loads(body)
            if status == 200 and all(f in data for f in fields):
                ok += 1
                print(f"  OK  free  {path} ({status}, fields {fields})")
            else:
                bad += 1
                print(f"  FAIL free  {path}: status={status} fields_missing="
                      f"{[f for f in fields if f not in data]}")
        except Exception as e:
            bad += 1
            print(f"  FAIL free  {path}: {e}")

    for label, path, query in PAID:
        try:
            status, headers, body = fetch(path, query)
            pay = headers.get("payment-required") or headers.get("Payment-Required")
            if status != 402 or not pay:
                bad += 1
                print(f"  FAIL paid {label}: status={status}, payment-required header missing")
                continue
            req_doc = json.loads(base64.b64decode(pay))
            # x402 v2: x402Version lives at the TOP level; per-route terms
            # (scheme/amount/payTo/network) live inside accepts[0]. Verified
            # live 2026-09-04 (hash-preview b64 decode): {"x402Version":2,
            # "resource":{...},"accepts":[{"scheme":"exact","network":
            # "eip155:8453","amount":"1000","asset":"0x83..","payTo":"0x40.."}]}
            acc = (req_doc.get("accepts") or [{}])[0]
            if req_doc.get("x402Version") == 2 and acc.get("scheme") == "exact" \
                    and str(acc.get("amount", "")).isdigit() and acc.get("payTo") \
                    and acc.get("network") == "eip155:8453":
                ok += 1
                usd = int(acc["amount"]) / 1e6
                print(f"  OK  paid  {label}: 402 x402v2 exact amount={acc['amount']} (${usd:.3f})")
            else:
                bad += 1
                print(f"  FAIL paid {label}: unexpected payment-required shape: {req_doc}")
        except Exception as e:
            bad += 1
            print(f"  FAIL paid {label}: {e}")

    print(f"\nresult: {ok} ok, {bad} failed of {ok + bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
