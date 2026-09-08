# SigTAP MCP Server (this repo)

Runnable stdio MCP server wrapping the SigTAP Outreach API (x402 micro-tools,
USDC on Base mainnet, facilitator PayAI). Zero dependencies: Python 3 stdlib only.

- `catalog`, `score_preview`, `hash_preview` — FREE, no wallet needed.
- Paid tools ($0.001–$0.01/call) proxy the live API; without a payment the API's
  real HTTP 402 block is returned so an x402-aware client can settle and retry.

## Run (stdio)

```bash
python3 mcp_server.py
# or
docker build -t sigtap-agent-tools . && docker run -i --rm sigtap-agent-tools
```

Claude Desktop / any MCP client config:

```json
{
  "mcpServers": {
    "sigtap-agent-tools": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "sigtap-agent-tools"]
    }
  }
}
```

Framing: Content-Length (MCP spec) or line-delimited JSON — auto-detected.

## Hosted endpoint (payments settled in-band)

`https://sigtap-mcp.sigtap.workers.dev/mcp` — Streamable HTTP,
13 tools, x402 v2. On paid tool calls the payment travels in
`params._meta["x402/payment"]` and the on-chain USDC receipt returns in
`result._meta["x402/payment-response"]` (the official `@x402/mcp` contract).
Health: `/health`. Server card: `/.well-known/mcp/server-card.json`.
Wire-level guide with live-verified request/response bodies:
[MCP.md](MCP.md).

## Docs

- HTTP API OpenAPI: https://sigtap-outreach-api.sigtap.workers.dev/openapi.json
- llms.txt: https://sigtap-outreach-api.sigtap.workers.dev/llms.txt
