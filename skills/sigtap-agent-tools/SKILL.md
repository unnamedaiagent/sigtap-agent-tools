---
name: sigtap-agent-tools
description: Pay-per-call micro-tools for AI agents over x402 (USDC on Base) - email deliverability audit, cold-email grading, templates, hashing, JWT decode, UUID, slug, JSON, regex, crypto price, domain age, weather. No signup, no API keys; free preview for every tool.
---

# sigtap Agent Tools (x402 skill)

Paid micro-API for agents. HTTP 402 + USDC on Base (eip155:8453) via the PayAI
facilitator. No accounts, no keys - the signed payment is the credential.
Free preview routes let you verify the output shape before paying anything.

## MCP server (same 13 tools)

Streamable HTTP: `https://sigtap-mcp.sigtap.workers.dev/mcp`
Free `catalog` tool lists all prices. The plugin manifest
(`.claude-plugin/plugin.json`) ships this server inline, so installing the
plugin registers the MCP server automatically.

## Paid endpoints (GET unless noted)

| Endpoint | Price | What you get |
|---|---|---|
| `/deliverability?domain=example.com` | $0.003 | 12-point sending-domain audit: SPF, DKIM, DMARC, MX, blocklists, age |
| `/grade?subject=...&body=...` | $0.005 | 12-point cold-email score with concrete fixes |
| `/template?persona=founder&offer=...` | $0.01 | personalized cold email from proven templates |
| `/tools/hash?text=...` | $0.0005 | SHA-256/384/512 + hex/base64/base64url/CRC32 |
| `/tools/jwt-decode?token=...` | $0.001 | JWT header+payload with safety flags (never verifies signatures) |
| `/tools/uuid?count=5&version=v4` | $0.0005 | batch random IDs (v4/v7/ulid/nanoid, crypto-secure) |
| `/tools/slug?text=...` | $0.001 | unicode URL slug, latin + Cyrillic transliteration |
| `/tools/json?data=...&mode=flatten` | $0.001 | flatten JSON to dot paths or rows->CSV |
| `/tools/regex?pattern=...&text=...` | $0.001 | matches with groups + ReDoS backtracking risk |
| `/tools/crypto-price?from=BTC&to=USD` | $0.002 | Coinbase spot/buy/sell + spread |
| `/tools/domain-age?domain=example.com` | $0.003 | RDAP registration date, age in days, registrar |
| `/tools/weather?lat=52.52&lon=13.41` | $0.001 | current conditions + 3h forecast (city query also works) |

## Free touch (verify shape before paying)

- `GET https://sigtap-outreach-api.sigtap.workers.dev/preview/<paid-path>` -
  free truncated sample of ANY paid tool (e.g. `/preview/tools/hash?text=hi`),
  locked demo input, response carries `paid_unlocks`
- `GET /` - full live index; `GET /health` - liveness

## Pay in one call (copy-paste)

```js
// npm i @x402/fetch viem
import { wrapFetchWithPayment } from "@x402/fetch";

const paidFetch = wrapFetchWithPayment(fetch, { address: "<your-wallet>" }); // Base mainnet USDC
const r = await paidFetch(
  "https://sigtap-outreach-api.sigtap.workers.dev/tools/uuid?count=5&version=v7"
);
console.log(r.status, await r.json()); // 200, settled on-chain ($0.0005)
```

Under the hood: call the endpoint -> `402` with terms in the base64
`PAYMENT-REQUIRED` header -> sign the USDC payment (Base) -> retry with
`PAYMENT-SIGNATURE` (x402 v2; legacy v1 clients use `X-PAYMENT`).

MCP one-liner (paid calls settle in-band; paste into any MCP client config):

```json
{ "mcpServers": { "sigtap-agent-tools": { "type": "http", "url": "https://sigtap-mcp.sigtap.workers.dev/mcp" } } }
```

## Client notes (avoid a silent 403)

The API sits behind Cloudflare. Set any real User-Agent (`requests`, `httpx`,
`curl`, `axios` - `python-urllib`'s default is blocked). Query params are
spelled out in the OpenAPI doc: https://sigtap-outreach-api.sigtap.workers.dev/openapi.json

## Links

- Catalog/README: https://github.com/unnamedaiagent/sigtap-agent-tools
- Official MCP Registry entry: `io.github.unnamedaiagent/sigtap-agent-tools`
- Human kit ($19): https://unnamedaiagent.github.io/sigtap-kit/
