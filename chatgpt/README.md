# ChatGPT bridge (planned private access)

This is a thin integration boundary around `/Users/steven/fiverr/local`.
The local package remains the only implementation of Seller OS domain logic,
the only MCP server, and the only canonical state owner.

The current bridge deliverable is deliberately local. Run it from the package
that declares the MCP dependency:

```sh
cd /Users/steven/fiverr/local
uv run python ../chatgpt/verify_chatgpt_connection.py
```

This launches the existing stdio MCP server against temporary state and does
not contact ChatGPT or any network.

## Safe progression

1. Verify the local stdio contract with synthetic state.
2. If private ChatGPT connectivity is enabled for the account, configure the
   vendor-supported secure tunnel outside this repository and begin with the
   read-only policy in `tool-policy.md`.
3. Treat `changeset_propose` as proposal-only. Keep local human approval for
   `changeset_approve`, project mutations, and every Fiverr editor action.

No Cloudflare deployment, public endpoint, Fiverr login, browser worker,
credential, or second database belongs in this bridge.

See `secure-tunnel/README.md` for the future access boundary and
`synthetic-test-state/README.md` for test-state rules.
