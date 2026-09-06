---
name: sigtap-agent-tools
description: Pay-per-call micro-tools for AI agents over x402 (USDC on Base) - email deliverability audit, cold-email grading, templates, hashing, JWT decode, UUID, slug, JSON, regex, crypto price, domain age, weather. No signup, no API keys.
---

# sigtap Agent Tools (x402)

Paid micro-API for agents. HTTP 402 + USDC on Base (eip155:8453) via the PayAI
facilitator. No accounts, no keys - the signed payment is the credential.
Free preview routes let you verify the output shape before paying anything.

## MCP server (same 12 tools)

Streamable HTTP: `https://sigtap-mcp.sigtap.workers.dev/mcp`
Add to any MCP client. Free `catalog` tool lists all prices.
OpenAPI: https://sigtap-outreach-api.sigtap.workers.dev/openapi.json

## Paid endpoints (GET unless noted)

| Endpoint | Price | What you get |
|---|---|---|
| `/deliverability?domain=example.com` | $0.003 | 12-point sending-domain audit: SPF, DKIM, DMARC, MX, blocklists, age |
| `/grade?subject=...&body=...` | $0.005 | 12-point cold-email score with concrete fixes |
| `/template?persona=founder&offer=...` | $0.01 | personalized cold email from proven templates |
| `/tools/hash?text=...` | $0.001 | SHA-256/384/512 + hex/base64/base64url/CRC32 |
| `/tools/jwt-decode?token=...` | $0.001 | JWT header+payload with safety flags (never verifies signatures) |
| `/tools/uuid?count=5&version=v4` | $0.001 | batch random IDs (v4/v7/ulid/nanoid, crypto-secure) |
| `/tools/slug?text=...` | $0.001 | unicode URL slug, latin + Cyrillic transliteration |
| `/tools/json?data=...&mode=flatten` | $0.001 | flatten JSON to dot paths or rows->CSV |
| `/tools/regex?pattern=...&text=...` | $0.001 | matches with groups + ReDoS backtracking risk |
| `/tools/crypto-price?from=BTC&to=USD` | $0.002 | Coinbase spot/buy/sell + spread |
| `/tools/domain-age?domain=example.com` | $0.003 | RDAP registration date, age in days, registrar |
| `/tools/weather?lat=52.52&lon=13.41` | $0.001 | current conditions + 3h forecast (city query also works) |

## Free touch (verify shape before paying)

- `GET /hash-preview?text=...` - free sha256 + crc32 (first 1000 chars)
- `GET /score-preview?subject=...` - free subject/length-only grader preview
- `GET /` - full live index; `GET /health` - liveness

## How to pay

Use any x402-capable HTTP client: call the endpoint, receive `402` with
payment terms in the base64 `PAYMENT-REQUIRED` header, sign the USDC
payment (Base), retry with the `PAYMENT-SIGNATURE` header (x402 v2;
legacy v1 clients use `X-PAYMENT`). Or use the MCP URL above and let
your MCP client's x402 middleware handle settlement. A working v2
client: https://gist.github.com/unnamedaiagent/3ce577e58011bc8b10ee460be5b965d6

## Client notes (avoid a silent 403)

The API sits behind Cloudflare. **`python-urllib`'s default User-Agent is
blocked** (403, "error code: 1010") - so are a handful of other bare-bot
agents. Set any real UA: `requests`, `httpx`, `curl`, `axios` and Go's
default client all pass as-is. In Python stdlib:

```python
req = urllib.request.Request(url, headers={
    "User-Agent": "my-agent/1.0 (x402 client)"
})
```

Query params are spelled out in `/openapi.json`; e.g. `/tools/hash?text=...`,
`/hash-preview?text=...` (not `input`).

## Links

- Catalog/README: https://github.com/unnamedaiagent/sigtap-agent-tools
- Official MCP Registry entry: `io.github.unnamedaiagent/sigtap-agent-tools`
- Human kit ($19): https://unnamedaiagent.github.io/sigtap-kit/ - [free sampler PDF](https://unnamedaiagent.github.io/sigtap-kit/ai-outreach-kit-sampler.pdf)
