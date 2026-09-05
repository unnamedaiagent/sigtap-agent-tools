#!/usr/bin/env python3
"""PitchPilot Agent Tools - MCP server (stdio, zero-dependency).

Wraps the PitchPilot Outreach API (x402 paid micro-tools, USDC on Base)
as MCP tools. Design:

- `catalog` tool and two free-preview tools work with NO wallet.
- Paid tools proxy to the live x402 API. When the caller has no payment
  attached, the API answers HTTP 402 and this server returns that real
  payment-required block so an x402-aware client can settle it.
- Stdio transport with automatic framing: Content-Length (LSP-style, per
  the MCP spec) or line-delimited JSON - whichever the client sends.

The production hosted endpoint (streamable HTTP, same tools, payments
settled in-band) is https://pitchpilot-mcp.pitchpilot-agents.workers.dev/mcp
"""

import json
import sys
import urllib.parse
import urllib.request

API = "https://pitchpilot-outreach-api.pitchpilot-agents.workers.dev"
MCP_URL = "https://pitchpilot-mcp.pitchpilot-agents.workers.dev/mcp"
PROTOCOL_VERSION = "2024-11-05"

# ---------------------------------------------------------------------------
# Tool catalog: mirrors the live API (https://.../openapi.json)
# price = USD per call, settled in USDC on Base mainnet via the PayAI
# facilitator. "free" tools need no payment at all.
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "catalog",
        "description": "List all PitchPilot tools with prices and free previews. Free, no payment required.",
        "price": 0.0,
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "score_preview",
        "description": "FREE preview of the 12-point cold email grader: scores a subject line only.",
        "price": 0.0,
        "inputSchema": {
            "type": "object",
            "properties": {"subject": {"type": "string", "description": "Email subject line to score"}},
            "required": ["subject"],
        },
    },
    {
        "name": "hash_preview",
        "description": "FREE hash preview: SHA-256 and CRC32 of a string (truncated at 1000 chars).",
        "price": 0.0,
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to hash"}},
            "required": ["text"],
        },
    },
    {
        "name": "deliverability_audit",
        "description": "SPF/DKIM/DMARC deliverability audit for a sending domain, with fixes. $0.003/call.",
        "price": 0.003,
        "inputSchema": {
            "type": "object",
            "properties": {"domain": {"type": "string", "description": "Sending domain, e.g. openai.com"}},
            "required": ["domain"],
        },
    },
    {
        "name": "email_grade",
        "description": "12-point cold email score with concrete fixes (subject + body). $0.005/call.",
        "price": 0.005,
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"},
            },
        },
    },
    {
        "name": "email_template",
        "description": "Personalized cold email from proven templates (persona, offer, name, company). $0.01/call.",
        "price": 0.01,
        "inputSchema": {
            "type": "object",
            "properties": {
                "persona": {"type": "string", "description": "Who you are / your role"},
                "offer": {"type": "string", "description": "What you offer"},
                "name": {"type": "string", "description": "Recipient name"},
                "company": {"type": "string", "description": "Recipient company"},
            },
        },
    },
    {
        "name": "domain_age",
        "description": "Domain age + registrar via RDAP - a proxy for prospect legitimacy. $0.003/call.",
        "price": 0.003,
        "inputSchema": {
            "type": "object",
            "properties": {"domain": {"type": "string", "description": "Domain to look up"}},
            "required": ["domain"],
        },
    },
    {
        "name": "crypto_price",
        "description": "Spot crypto price conversion (e.g. BTC/USD). $0.002/call.",
        "price": 0.002,
        "inputSchema": {
            "type": "object",
            "properties": {
                "from": {"type": "string", "description": "Base asset symbol, e.g. BTC"},
                "to": {"type": "string", "description": "Quote asset symbol, e.g. USD"},
            },
            "required": ["from", "to"],
        },
    },
    {
        "name": "jwt_decode",
        "description": "Decode a JWT (header/payload) with expiry and safety flags. No signature check. $0.001/call.",
        "price": 0.001,
        "inputSchema": {
            "type": "object",
            "properties": {"token": {"type": "string", "description": "JWT string"}},
            "required": ["token"],
        },
    },
    {
        "name": "hash_suite",
        "description": "SHA-256/384/512, hex, base64, base64url, CRC32 of a UTF-8 string. $0.001/call.",
        "price": 0.001,
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to hash"}},
            "required": ["text"],
        },
    },
    {
        "name": "uuid_batch",
        "description": "Batch-generate UUIDs (v4). $0.001/call.",
        "price": 0.001,
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "How many (default 5)"},
                "version": {"type": "string", "description": "UUID version (default v4)"},
            },
        },
    },
    {
        "name": "slugify",
        "description": "URL-safe slug from text, optional max length. $0.001/call.",
        "price": 0.001,
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to slugify"},
                "maxlength": {"type": "integer", "description": "Max slug length"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "json_tools",
        "description": "Validate / minify / pretty-print JSON. $0.001/call.",
        "price": 0.001,
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON string"},
                "mode": {"type": "string", "description": "validate|minify|pretty (default validate)"},
            },
            "required": ["data"],
        },
    },
    {
        "name": "regex_tester",
        "description": "Test a regex against text with ReDoS safety check. $0.001/call.",
        "price": 0.001,
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regular expression"},
                "text": {"type": "string", "description": "Text to test against"},
                "flags": {"type": "string", "description": "Regex flags, e.g. gi"},
            },
            "required": ["pattern", "text"],
        },
    },
    {
        "name": "weather",
        "description": "Current weather by lat/lon (for geo-aware messaging). $0.001/call.",
        "price": 0.001,
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lon": {"type": "number", "description": "Longitude"},
            },
            "required": ["lat", "lon"],
        },
    },
]

# tool name -> (API path, query args)
ROUTES = {
    "score_preview": ("/score-preview", ["subject"]),
    "hash_preview": ("/hash-preview", ["text"]),
    "deliverability_audit": ("/deliverability", ["domain"]),
    "email_grade": ("/grade", ["subject", "body"]),
    "email_template": ("/template", ["persona", "offer", "name", "company"]),
    "hash_suite": ("/tools/hash", ["text"]),
    "jwt_decode": ("/tools/jwt-decode", ["token"]),
    "uuid_batch": ("/tools/uuid", ["count", "version"]),
    "slugify": ("/tools/slug", ["text", "maxlength"]),
    "json_tools": ("/tools/json", ["data", "mode"]),
    "regex_tester": ("/tools/regex", ["pattern", "text", "flags"]),
    "crypto_price": ("/tools/crypto-price", ["from", "to"]),
    "domain_age": ("/tools/domain-age", ["domain"]),
    "weather": ("/tools/weather", ["lat", "lon"]),
}

CATALOG_TEXT = "\n".join(
    "{} - {} ${:.3f}/call{}".format(
        t["name"],
        t["description"].split(".")[0],
        t["price"],
        "  [FREE]" if t["price"] == 0 else "",
    )
    for t in TOOLS
)

PAYMENT_NOTE = (
    "Payment required: x402 (USDC on Base mainnet, facilitator PayAI). "
    "An x402-aware client signs the payment from the 402 block above and retries. "
    "Hosted streamable-HTTP MCP endpoint with in-band payments: " + MCP_URL
)


def api_get(path, args):
    """GET the API. Returns (status, text)."""
    qs = {k: str(v) for k, v in args.items() if v is not None}
    url = API + path
    if qs:
        url += "?" + urllib.parse.urlencode(qs)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "pitchpilot-agent-tools/1.0 (MCP stdio server)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # network error
        return 0, json.dumps({"error": str(e)})


def call_tool(name, arguments):
    if name == "catalog":
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "PitchPilot Agent Tools - x402 micro-tools, USDC on Base.\n"
                        "Free previews: score_preview, hash_preview.\n\n" + CATALOG_TEXT
                    ),
                }
            ]
        }

    if name not in ROUTES:
        raise ValueError("Unknown tool: " + name)

    path, argnames = ROUTES[name]
    args = {k: arguments.get(k) for k in argnames if k in arguments}
    status, text = api_get(path, args)

    if status == 200:
        return {"content": [{"type": "text", "text": text}]}
    if status == 402:
        # Real payment-required response from the x402 API - pass it through
        # so an x402-aware client can settle and retry.
        return {
            "content": [{"type": "text", "text": text[:4000]}],
            "isError": True,
            "_meta": {"paymentRequired": True, "howToPay": PAYMENT_NOTE},
        }
    return {
        "content": [{"type": "text", "text": "API error HTTP {}: {}".format(status, text[:2000])}],
        "isError": True,
    }


# ---------------------------------------------------------------------------
# JSON-RPC plumbing
# ---------------------------------------------------------------------------

def handle(msg):
    method = msg.get("method")
    mid = msg.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": (msg.get("params") or {}).get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "serverInfo": {"name": "pitchpilot-agent-tools", "version": "1.0.0"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        tools = []
        for t in TOOLS:
            entry = {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
            if t["price"] > 0:
                entry["_meta"] = {
                    "io.modelcontextprotocol.registry/payment": {
                        "scheme": "x402",
                        "network": "eip155:8453",
                        "asset": "USDC",
                        "priceUsd": t["price"],
                    }
                }
            tools.append(entry)
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": tools}}
    if method == "tools/call":
        params = msg.get("params") or {}
        try:
            result = call_tool(params.get("name"), params.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": mid, "result": result}
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {"content": [{"type": "text", "text": "Error: {}".format(e)}], "isError": True},
            }
    if method in ("resources/list", "prompts/list"):
        return {"jsonrpc": "2.0", "id": mid, "result": {method.split("/")[0]: []}}
    if mid is None:
        return None  # notification
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "Method not found: " + str(method)}}


def read_message(stream):
    """Read one JSON-RPC message.

    Supports Content-Length framing (MCP spec) and line-delimited JSON.
    Returns (msg, framed) where framed=False means line mode; (None, _) on EOF.
    """
    first = stream.readline()
    if not first:
        return None, False
    stripped = first.strip()
    if stripped.lower().startswith(b"content-length:"):
        length = int(stripped.split(b":", 1)[1].strip())
        while True:  # consume rest of headers
            line = stream.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
        body = stream.read(length)
        if not body:
            return None, True
        return json.loads(body.decode("utf-8")), True
    if not stripped:
        return None, False
    return json.loads(stripped.decode("utf-8")), False


def write_message(msg, framed):
    data = json.dumps(msg).encode("utf-8")
    out = sys.stdout.buffer
    if framed:
        out.write(b"Content-Length: %d\r\n\r\n%s" % (len(data), data))
    else:
        out.write(data + b"\n")
    out.flush()


def main():
    stream = sys.stdin.buffer
    while True:
        try:
            msg, framed = read_message(stream)
        except Exception:
            continue
        if msg is None:
            break  # EOF: no more input
        resp = handle(msg)
        if resp is not None:
            write_message(resp, framed)


if __name__ == "__main__":
    main()
