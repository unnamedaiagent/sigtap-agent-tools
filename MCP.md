# Paying the hosted sigtap MCP server over x402 (wire-level guide)

Hosted endpoint: `https://sigtap-mcp.sigtap.workers.dev/mcp` — Streamable HTTP,
13 tools (12 paid + free `catalog`), x402 v2 payments settled in-band
(USDC on Base, PayAI facilitator). Stateless: no session id, one POST per call.

Prices: $0.001–$0.01 per tool call, listed in each tool's description and in
the free `catalog` tool. No signup, no API keys — a signed payment is the credential.

Every JSON block below is copied from a live run on 2026-09-08, including the
settled transaction. If this document and the server ever disagree, please open an issue.

## TL;DR for x402-aware MCP clients

Any client built on the official `@x402/mcp` contract just works: on an unpaid
paid-tool call you get the challenge, you sign, you retry with
`params._meta["x402/payment"]`, the receipt comes back in
`result._meta["x402/payment-response"]`. No HTTP headers involved.

## Manual flow (what your client does under the hood)

### 1. Initialize (optional but polite)

```json
POST /mcp
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
  "protocolVersion":"2025-06-18","capabilities":{},
  "clientInfo":{"name":"my-agent","version":"1.0"}}}
```

- The `Accept` header MUST list **both** `application/json` and
  `text/event-stream`. Sending only `application/json` fails with
  `{"code":-32000,"message":"Not Acceptable: Client must accept both application/json and text/event-stream"}`.
- The server is stateless: it returns no `Mcp-Session-Id` and you don't need one.

### 2. Free discovery

```json
POST /mcp
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"catalog","arguments":{}}}
```

Returns every tool with `price_usd`, plus free HTTP preview routes you can try
with no wallet at all (`/preview/<tool>` on the API host).

### 3. Call a paid tool without paying — get the challenge

```json
POST /mcp
{"jsonrpc":"2.0","id":3,"method":"tools/call",
 "params":{"name":"hash_text","arguments":{"text":"hello"}}}
```

The HTTP status is **200** (this is JSON-RPC, not a bare HTTP 402), and the
result carries the x402 challenge:

```json
{"result":{
  "content":[{"type":"text","text":"{\"x402Version\":2,\"error\":\"Payment required to access this tool\",\"resource\":{\"url\":\"mcp://tool/hash_text\",\"description\":\"SHA-256/384/512, hex, base64, base64url and CRC32 of a UTF-8 string ($0.001)\",\"mimeType\":\"application/json\"},\"accepts\":[{\"scheme\":\"exact\",\"network\":\"eip155:8453\",\"amount\":\"1000\",\"asset\":\"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913\",\"payTo\":\"0x963d450CA601d52B5D92a8540Aea8D4272223ae1\",\"maxTimeoutSeconds\":60,\"extra\":{\"name\":\"USD Coin\",\"version\":\"2\"}}]}"}],
  "isError":true}}
```

Parse `content[0].text` as JSON. Notes:

- `amount` is in USDC base units (6 decimals): `"1000"` = $0.001.
- `resource.url` is an `mcp://tool/<name>` identifier — use it verbatim in the
  payment payload, never fetch it.
- Treat this as your 402: check `result.isError`, not the HTTP status.

### 4. Sign the payment (EIP-3009 transfer-with-authorization)

Sign an EIP-712 `TransferWithAuthorization` for the USDC contract from the
challenge:

- domain: `{name: "USD Coin", version: "2", chainId: 8453, verifyingContract: <accepts[0].asset>}`
- types: `from address, to address, value uint256, validAfter uint256, validBefore uint256, nonce bytes32`
- message: your address, `payTo` as `to`, the exact `amount`, `validAfter: 0`,
  `validBefore: now + 300`, fresh 32-byte `nonce`.

No gas, no approval — the facilitator submits the transfer after verifying your
signature.

### 5. Retry with the payment in `_meta`

Same method, same arguments, plus the signed payload in
`params._meta["x402/payment"]`:

```json
POST /mcp
{"jsonrpc":"2.0","id":4,"method":"tools/call",
 "params":{"name":"hash_text","arguments":{"text":"hello"},
   "_meta":{"x402/payment":{
     "x402Version":2,
     "payload":{"authorization":{"from":"0x…","to":"0x963d450CA601d52B5D92a8540Aea8D4272223ae1","value":"1000","validAfter":"0","validBefore":"1757…","nonce":"0x…"},
                "signature":"0x…"},
     "resource":{"url":"mcp://tool/hash_text","description":"…","mimeType":"application/json"},
     "accepted":{"scheme":"exact","network":"eip155:8453","amount":"1000","asset":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","payTo":"0x963d450CA601d52B5D92a8540Aea8D4272223ae1","maxTimeoutSeconds":60,"extra":{"name":"USD Coin","version":"2"}}}}}}
```

`authorization`, `resource` and `accepted` are exactly what the challenge gave
you (only `from`, `validBefore`, `nonce` are yours, plus the signature).

### 6. Result + on-chain receipt

```json
{"result":{
  "content":[{"type":"text","text":"{\"length\":33,\"byte_length\":33,\"sha256\":\"713583…2519\", …}"}],
  "_meta":{"x402/payment-response":{
    "success":true,
    "payer":"0x2706b0680e5d724F34A023D4dfcD08739d923E54",
    "transaction":"0x5de43ef45b95272b9bb9ad242a088f900ce61fd5de4a971279cf5856626fa3e3",
    "network":"eip155:8453"}}}}
```

`transaction` is the settled USDC transfer on Base — look it up on
Basescan to verify. Every signature pays for exactly one call.

## Minimal Node client (zero MCP SDK, verified end-to-end 2026-09-08)

Requires `npm i viem@2 viem/accounts` (or the `viem` meta package). This exact
script shape produced the receipt in step 6.

```js
import { privateKeyToAccount } from "viem/accounts";

const MCP = "https://sigtap-mcp.sigtap.workers.dev/mcp";
const acct = privateKeyToAccount(process.env.EVM_PRIVATE_KEY); // funded on Base
const b64 = (s) => Buffer.from(s, "utf8").toString("base64");

async function rpc(id, method, params = {}, headers = {}) {
  const res = await fetch(MCP, {
    method: "POST",
    // both content types are REQUIRED:
    headers: { "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream", ...headers },
    body: JSON.stringify({ jsonrpc: "2.0", id, method, params }),
  });
  return (await res.json());
}

await rpc(1, "initialize", { protocolVersion: "2025-06-18", capabilities: {},
                             clientInfo: { name: "demo", version: "1" } });

// challenge
const unpaid = await rpc(2, "tools/call", { name: "hash_text", arguments: { text: "hello" } });
if (!unpaid.result?.isError) throw new Error("expected a payment challenge");
const req = JSON.parse(unpaid.result.content[0].text);
const a = req.accepts[0];

// sign EIP-3009 TransferWithAuthorization
const authorization = {
  from: acct.address, to: a.payTo, value: a.amount,
  validAfter: "0", validBefore: String(Math.floor(Date.now() / 1000) + 300),
  nonce: "0x" + crypto.getRandomValues(new Uint8Array(32)).reduce((s, b) => s + b.toString(16).padStart(2, "0"), ""),
};
const signature = await acct.signTypedData({
  domain: { name: a.extra.name, version: a.extra.version, chainId: 8453, verifyingContract: a.asset },
  types: { TransferWithAuthorization: [
    { name: "from", type: "address" }, { name: "to", type: "address" },
    { name: "value", type: "uint256" }, { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" }, { name: "nonce", type: "bytes32" }] },
  primaryType: "TransferWithAuthorization", message: authorization,
});

// paid retry: payment goes IN-BAND in params._meta — not in an HTTP header
const paid = await rpc(3, "tools/call", {
  name: "hash_text", arguments: { text: "hello" },
  _meta: { "x402/payment": { x402Version: 2,
    payload: { authorization, signature }, resource: req.resource, accepted: a } },
});
console.log(paid.result.content[0].text);         // tool result
console.log(paid.result._meta["x402/payment-response"]); // {success, payer, transaction, network}
```

## Gotchas

- **Accept header**: must be `application/json, text/event-stream` — a
  JSON-only Accept gets `-32000 Not Acceptable` before anything else runs.
- **HTTP 200 ≠ paid result**: unpaid paid-tool calls return 200 with
  `isError: true` and the challenge in `content[0].text`. Check `isError`.
- **Header-based payment does not work on MCP**: `PAYMENT-SIGNATURE` /
  `X-PAYMENT` headers are the *HTTP API* contract
  (https://sigtap-outreach-api.sigtap.workers.dev — see the
  [x402 snippets gist](https://gist.github.com/unnamedaiagent/3ce577e58011bc8b10ee460be5b965d6)).
  The MCP server reads only `params._meta["x402/payment"]`.
- **One signature, one call**: retries after an error need a fresh nonce.
- **Stateless**: no `Mcp-Session-Id` round-trip is needed; every POST stands alone.
- Settlement happens through the PayAI facilitator right after verification;
  a transient facilitator hiccup surfaces as an `isError` result — sign again
  and retry.

## Also available

- Free previews of every tool, no wallet: `GET https://sigtap-outreach-api.sigtap.workers.dev/preview/<tool>`
- HTTP API with header-based payments: [README](README.md) +
  [gist with verified Node/Python clients](https://gist.github.com/unnamedaiagent/3ce577e58011bc8b10ee460be5b965d6)
- Runnable stdio server (this repo): [SERVER.md](SERVER.md)
- Skill for SKILL.md-aware agents: [SKILL.md](SKILL.md)
