# llms-install.md — sigtap Agent Tools (MCP)

Instructions for AI agents (Cline, Claude, Cursor, ...) installing this MCP
server from this repository alone. Two ways to run it; the remote URL needs
zero installs.

## What you get

13 tools over MCP: `catalog` (free), `score_preview` + `hash_preview` (free
previews), and 10 paid micro-tools — `deliverability_audit`, `email_grade`,
`email_template`, `domain_age`, `crypto_price`, `jwt_decode`, `hash_suite`,
`uuid_batch`, `slugify`, `json_tools`, `regex_tester`, `weather` — priced
$0.001–$0.01/call, settled x402 (USDC on Base, PayAI facilitator). No signup,
no API keys: a wallet-capable client auto-signs per call. Free tools work with
any client, no wallet.

## Option A — Remote (recommended, no files needed)

Streamable HTTP endpoint:

```
https://sigtap-mcp.sigtap.workers.dev/mcp
```

Claude Code:

```bash
claude mcp add --transport http sigtap \
  https://sigtap-mcp.sigtap.workers.dev/mcp
```

Generic MCP client JSON:

```json
{
  "mcpServers": {
    "sigtap": {
      "type": "http",
      "url": "https://sigtap-mcp.sigtap.workers.dev/mcp"
    }
  }
}
```

Verify: call the free `catalog` tool — it returns the full price list with no
wallet. Health check: `GET https://sigtap-mcp.sigtap.workers.dev/health`.

## Option B — Local stdio (zero dependencies, Python 3 stdlib only)

```bash
git clone https://github.com/unnamedaiagent/sigtap-agent-tools.git
cd sigtap-agent-tools
python3 mcp_server.py
```

Or Docker:

```bash
docker build -t sigtap-agent-tools .
docker run -i --rm sigtap-agent-tools
```

Client config:

```json
{
  "mcpServers": {
    "sigtap-agent-tools": {
      "command": "python3",
      "args": ["mcp_server.py"]
    }
  }
}
```

The stdio server accepts both Content-Length framing (MCP spec) and
line-delimited JSON. It wraps the same hosted API; paid tool calls without a
payment return the API's real HTTP 402 block so an x402-aware client can
settle and retry.

## Calling the HTTP API directly (no MCP)

OpenAPI: https://sigtap-outreach-api.sigtap.workers.dev/openapi.json
Human/LLM docs: https://sigtap-outreach-api.sigtap.workers.dev/llms.txt

Free probes:
- `GET /api/v1/hash-preview?text=hello`
- `GET /api/v1/score-preview?text=Hi Bob, quick question about your roadmap`

Send a normal browser-like User-Agent (e.g. `Mozilla/5.0`); bare
`python-urllib` UAs are blocked by our CDN with error 1010.

## Paid calls

Each paid endpoint answers HTTP 402 with a base64 `payment-required` header
carrying x402 v2 requirements (scheme `exact`, network `eip155:8453`, asset
USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, payTo
`0x4039237dEE97de393D9EDE537BED0AE4ABf0b69D`, amounts 1000–10000
micro-USDC). An x402 client signs, sends `payment` header, receives the
result. x402 library: https://x402.org
