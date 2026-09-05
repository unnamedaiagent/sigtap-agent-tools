# sigtap Agent Tools

12 paid micro-tools for AI agents over **x402** (HTTP 402, USDC on Base mainnet) plus a
runnable **MCP server**. Pay per call ($0.001-$0.01), no signup, no API keys -
the signed payment IS the credential.

- HTTP API: `https://sigtap-outreach-api.sigtap.workers.dev`
- MCP (Streamable HTTP): `https://sigtap-mcp.sigtap.workers.dev/mcp` (13 tools)
- Facilitator: PayAI (`eip155:8453`, asset USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
- Kit tier (humans): https://aioutreachkit.surge.sh - AI Outreach Kit, $19, crypto checkout

## Free touch (no wallet needed)

| Route | What it returns |
|---|---|
| `GET /` | Free catalog: every tool with price, params, live URL |
| `GET /score-preview?subject=...` | Subject-line-only preview of the email grader |
| `GET /hash-preview?text=...` | sha256 + crc32 of the first 1000 chars |
| `GET /openapi.json` | Full OpenAPI with `x-payment-info` prices |
| `GET /llms.txt` | Agent-readable endpoint digest |

## Paid endpoints (price live-verified from `/openapi.json`)

**Outreach intelligence (the money tools):**

| Endpoint | Price | Output |
|---|---|---|
| `GET /deliverability?domain=` | $0.003 | SPF/DKIM/DMARC audit for a sending domain |
| `GET /grade?to=&subject=&body=` | $0.005 | 12-point cold-email score with concrete fixes |
| `GET /template?...` | $0.010 | Personalized cold email from proven templates |

**Micro-tools ($0.001-$0.003):**

| Endpoint | Price | Output |
|---|---|---|
| `GET /tools/crypto-price?from=BTC&to=USD` | $0.002 | Coinbase spot/buy/sell + spread % |
| `GET /tools/domain-age?domain=` | $0.003 | Registration date, age, registrar (RDAP) |
| `GET /tools/hash?text=` | $0.001 | SHA-256/384/512, hex, base64(url), CRC32 |
| `GET /tools/json?data=` | $0.001 | Flatten to dot paths / rows to CSV |
| `GET /tools/jwt-decode?token=` | $0.001 | JWT header+payload with safety flags |
| `GET /tools/regex?pattern=&text=` | $0.001 | Matches, groups, count, ReDoS-risk heuristic |
| `GET /tools/slug?text=` | $0.001 | Unicode-safe slug (incl. Cyrillic translit) |
| `GET /tools/uuid?type=&count=` | $0.001 | UUIDv4/v7, ULID, nanoid - batched |
| `GET /tools/weather?lat=&lon=` | $0.001 | Current + next-3h temps (open-meteo) |

## x402 payment flow (one round-trip)

1. `GET /tools/hash?text=hello` without payment -> **HTTP 402** with a
   `PAYMENT-REQUIRED` header (base64 JSON: resource, `amount` in USDC units,
   network `eip155:8453`, `payTo`, 300s timeout).
2. Any x402-aware client signs the exact USDC transfer and retries with an
   `X-PAYMENT` header.
3. 200 + result. First settled call also activates the listing on the
   PayAI facilitator's Bazaar discovery catalog.

> **Heads-up:** the API is behind Cloudflare. Python's default
> `Python-urllib` User-Agent is blocked (403 error 1010). Any real UA
> works (`requests`, `httpx`, `curl`, `axios` pass as-is). Details in
> [SKILL.md](SKILL.md#client-notes-avoid-a-silent-403).

## MCP server

- **Hosted**: `https://sigtap-mcp.sigtap.workers.dev/mcp` -
  Streamable HTTP, 13 tools, x402 v2 payment settled in-band. Health: `/health`,
  card: `/.well-known/mcp/server-card.json`.
- **This repo** (`mcp_server.py`, Dockerfile): zero-dependency stdio server,
  Python 3 stdlib only. `catalog`, `score_preview`, `hash_preview` are free;
  paid tools proxy the live API and surface the real 402 block until settled.
  See [SERVER.md](SERVER.md). Registered in the Official MCP Registry as
  `io.github.unnamedaiagent/pitchpilot-agent-tools`.

## Agent integration

- Skill for Claude Code / any SKILL.md-aware agent: see [SKILL.md](SKILL.md)
  (indexed on skills.sh).
- Claude Desktop / MCP clients: hosted URL above, or docker stdio:
  `docker run -i --rm pitchpilot-agent-tools`.

Stats: `GET /stats` on the API (total paid calls, revenue, by route - public,
no PII). Pricing may be adjusted upward; `/openapi.json` is always live.
