# Secure tunnel boundary (future work)

This folder documents a future private-access boundary; it intentionally has
no tunnel command, no credentials, configuration, or network client.

When private ChatGPT access is actually enabled for the account, use the
vendor-supported Secure MCP Tunnel and point it at the existing local stdio
adapter. Confirm the account's current capabilities and authorization model
before enabling anything. Do not substitute a public URL, Cloudflare quick
tunnel, bearer token, or unauthenticated listener.

The first connection must expose only the read-only tools listed in
`../tool-policy.md`, use synthetic state, and pass `../verify_chatgpt_connection.py`
locally. Expand access only after reviewing tool descriptions and logs. Any
write-capable tool remains behind a local human approval boundary.

This document is not an instruction to connect now. It is a security checklist
for a separately reviewed future change.
