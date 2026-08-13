# Fiverr Seller OS — local runtime

This directory is the personal, local-first runtime for Seller OS. It exposes
the reviewed MCP tools over standard input/output and stores canonical state in
the application-owned SQLite database. No Fiverr request, browser action,
publication, upload, tunnel, or remote listener is part of this runtime.

## Setup

From this directory, run:

```sh
./scripts/setup.sh
```

The setup is safe to repeat. With `uv` installed it synchronizes the project
environment and development dependencies, then makes the local verification
scripts executable. It does not create production services or configure a
remote endpoint.

## Verify the MCP boundary

```sh
uv run python scripts/test_mcp.py
```

The check starts the actual `fiverr_seller_os.cli` stdio server in a temporary
isolated state directory, performs MCP initialization, confirms the exact 13
tool names, calls `seller_get_brief`, and removes the temporary database. A
successful run prints:

```text
MCP stdio check passed: 13 tools; seller_get_brief returned local-only state.
```

The application’s normal state location is selected by
`FIVERR_SELLER_OS_STATE_DIR` when set, or the platform application-data
location otherwise. The verification script always overrides it with a
temporary directory so it cannot inspect or modify personal state.

## Run the server locally

The MCP process itself is launched by an MCP host using:

```sh
uv run python -m fiverr_seller_os.cli
```

It communicates only over stdio. Keep stdout reserved for the MCP protocol;
diagnostic output should go to the host or stderr.
