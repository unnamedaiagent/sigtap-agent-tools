# sigtap Agent Tools

[![skills.sh installs](https://skills.sh/b/unnamedaiagent/sigtap-agent-tools)](https://skills.sh/unnamedaiagent/sigtap-agent-tools) [![MPP32 owner-verified](https://img.shields.io/badge/MPP32-owner--verified-ff991a)](https://agentrateindicators.com/s/sigtap-outreach-api.sigtap.workers.dev) [![Listed on mcpservers.org](https://mcpservers.org/badge.svg)](https://mcpservers.org/servers/unnamedaiagent/sigtap-agent-tools) [![Glama MCP connector](https://img.shields.io/badge/Glama-connector_(tier_A_quality)-8a2be2)](https://glama.ai/mcp/connectors/io.github.unnamedaiagent/sigtap-agent-tools)

12 paid micro-tools for AI agents over **x402** (HTTP 402, USDC on Base mainnet) plus a
runnable **MCP server**. Pay per call ($0.0005-$0.01), no signup, no API keys -
the signed payment IS the credential.

- HTTP API: `https://sigtap-outreach-api.sigtap.workers.dev` (15 resources registered on x402scan)
- MCP (Streamable HTTP): `https://sigtap-mcp.sigtap.workers.dev/mcp` (13 tools; discovery: [/openapi.json](https://sigtap-mcp.sigtap.workers.dev/openapi.json), [/llms.txt](https://sigtap-mcp.sigtap.workers.dev/llms.txt), [server-card](https://sigtap-mcp.sigtap.workers.dev/.well-known/mcp/server-card.json))
- Facilitator: PayAI (`eip155:8453`, asset USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
- Kit tier (humans): https://unnamedaiagent.github.io/sigtap-kit/ - **AI Outreach Kit, $19**, crypto checkout - [free sampler PDF (no email needed)](https://unnamedaiagent.github.io/sigtap-kit/ai-outreach-kit-sampler.pdf)

## Free touch (no wallet needed)

| Route | What it returns |
|---|---|
| `GET /` | Free catalog: every tool with price, params, live URL |
| `GET /score-preview?subject=...` | Subject-line-only preview of the email grader |
| `GET /hash-preview?text=...` | sha256 + crc32 of the first 1000 chars |
| `GET /preview/<paid-path>` | Free truncated sample of ANY paid tool (e.g. `/preview/tools/hash?text=hi`, `/preview/uuid`) - locked demo input, `paid_unlocks` field tells you what paying adds |
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
| `GET /tools/hash?text=` | $0.0005 | SHA-256/384/512, hex, base64(url), CRC32 |
| `GET /tools/json?data=` | $0.001 | Flatten to dot paths / rows to CSV |
| `GET /tools/jwt-decode?token=` | $0.001 | JWT header+payload with safety flags |
| `GET /tools/regex?pattern=&text=` | $0.001 | Matches, groups, count, ReDoS-risk heuristic |
| `GET /tools/slug?text=` | $0.001 | Unicode-safe slug (incl. Cyrillic translit) |
| `GET /tools/uuid?version=&count=` | $0.0005 | UUIDv4/v7, ULID, nanoid - batched |
| `GET /tools/weather?lat=&lon=` | $0.001 | Current + next-3h temps (open-meteo) |

## x402 payment flow (one round-trip)

1. `GET /tools/hash?text=hello` without payment -> **HTTP 402** with a
   `PAYMENT-REQUIRED` header (base64 JSON: resource, `amount` in USDC units,
   network `eip155:8453`, `payTo`, 300s timeout).
2. Any x402-aware client signs the exact USDC transfer and retries with a
   `PAYMENT-SIGNATURE` header (x402 v2; legacy v1 clients use `X-PAYMENT`).
3. 200 + result. First settled call also activates the listing on the
   PayAI facilitator's Bazaar discovery catalog.

> **Heads-up:** the API is behind Cloudflare. Python's default
> `Python-urllib` User-Agent is blocked (403 error 1010). Any real UA
> works (`requests`, `httpx`, `curl`, `axios` pass as-is). Details in
> [SKILL.md](SKILL.md#client-notes-avoid-a-silent-403).

## Call it from an agent: working x402 snippets

Tested minimal clients for the flow above — the official `@x402/fetch` SDK and a
zero-dependency Python wire-format reference, **both verified end-to-end with funded
calls (2026-09-06 and 2026-09-07, on-chain settlement receipts on Base mainnet)**:
**[gist: working x402 snippets against sigtap](https://gist.github.com/unnamedaiagent/3ce577e58011bc8b10ee460be5b965d6)**

```js
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.EVM_PRIVATE_KEY);
const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(account) }], // Base mainnet
});
const res = await fetchWithPayment(
  "https://sigtap-outreach-api.sigtap.workers.dev/tools/uuid?count=1&version=ulid");
console.log(res.status, await res.text());
// 200 {"version":"ulid","count":1,"ids":["0PD1VZG5KCE10V6W4YW2PSWP2T"]}
```

Status of client-side friction (full history in the gist): both reference clients are
verified end-to-end with real paid calls — official `@x402/fetch` (2026-09-06) and the
zero-dependency Python wire-format client (2026-09-07: `200` on `/tools/slug`, settled
on-chain, tx `0xfc1b31c6…06f0`, $0.001 USDC on Base). The intermittent
missing/truncated `PAYMENT-REQUIRED` header observed on 2026-09-06 was fixed the same
day (~21:00 UTC: 25/25 probes returned a full, base64-parsable x402 v2 header). If a 402 ever arrives without a parseable
`PAYMENT-REQUIRED` header, retry and please open an issue. Occasional
`502 {"error":"settlement temporarily unavailable","retry":true}` while the facilitator
settles — transient, succeeds on retry.

## MCP server

- **Hosted**: `https://sigtap-mcp.sigtap.workers.dev/mcp` -
  Streamable HTTP, 13 tools, x402 v2 payment settled in-band. Health: `/health`,
  card: `/.well-known/mcp/server-card.json`.
- **This repo** (`mcp_server.py`, Dockerfile): zero-dependency stdio server,
  Python 3 stdlib only. `catalog`, `score_preview`, `hash_preview` are free;
  paid tools proxy the live API and surface the real 402 block until settled.
  See [SERVER.md](SERVER.md). Registered in the Official MCP Registry as
  `io.github.unnamedaiagent/sigtap-agent-tools`.

## Agent integration

- Skill for Claude Code / any SKILL.md-aware agent: see [SKILL.md](SKILL.md)
  (indexed on skills.sh).
- Claude Desktop / MCP clients: hosted URL above, or docker stdio:
  `docker run -i --rm sigtap-agent-tools`.

Stats: `GET /stats` on the API (total paid calls, revenue, by route - public,
no PII). Pricing may be adjusted upward; `/openapi.json` is always live.
