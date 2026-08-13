# Future ChatGPT access runbook

This is a planning document for a future, private connection to the local
Seller OS. It is not a deployment procedure and it does not authorize opening
an endpoint, starting a tunnel, or granting an AI client write access.

## Current boundary

Version 1 remains Mac-local. The Python MCP server uses stdio, and the local
Seller OS database is the authority for profile, Gig, changeset, intake, and
project state. A personal ChatGPT Pro/Plus account is not assumed to have the
same connector, developer-mode, or write capabilities as a business-managed
workspace. ChatGPT access is therefore optional and must not be treated as an
approval mechanism for changes to canonical state.

Do not put any of the following into a prompt, tool argument, repository,
`.env` file, MCP response, or log:

- Fiverr passwords, API keys, OAuth tokens, session cookies, browser profiles,
  MFA/2FA codes, recovery codes, or payment information;
- buyer private data that is not needed for the specific local analysis; or
- secrets copied from a shell, browser, password manager, or environment.

## If private access is revisited

1. Verify the actual capabilities and account eligibility in the current
   ChatGPT account and current OpenAI documentation. Do not infer support from
   an old screenshot, a third-party tutorial, or a different account tier.
2. Prefer an OpenAI Secure MCP Tunnel for a private local development path. It
   must terminate at the local stdio/HTTP adapter intentionally selected for
   this project, run only while needed, and expose the smallest read-only tool
   set first. See the [Secure MCP Tunnels documentation](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
3. Start with `seller_get_brief`, `profile_get`, `gigs_list`, `gig_get`, and
   other read tools. Keep `changeset_propose` available only when its output
   is clearly a draft. `changeset_approve` remains a local human action with a
   current revision check; a ChatGPT conversation is not approval.
4. Use a disposable test database and synthetic records before pointing a
   connection at real seller state. Confirm that tool results contain no
   secrets, cookies, raw buyer text, or unexpected filesystem data.
5. Record the connection decision, exposed tool names, account scope, start
   and stop procedure, and rollback procedure in the project notes. Re-review
   after any SDK, ChatGPT, tunnel, or authentication change.

## Public HTTPS is a separate project

Do not substitute a quick Cloudflare tunnel, bearer token, shared secret, or
DNS record for an authenticated MCP deployment. If this service ever becomes
publicly reachable, it needs a separately reviewed HTTPS architecture,
OAuth 2.1 authorization, redirect/consent handling, token validation,
audience/scope checks, rate limits, audit logging, and a documented revocation
path. The [OpenAI MCP authentication guidance](https://developers.openai.com/plugins/build/auth)
is the baseline for that review. A random `trycloudflare.com` URL is not a
production security boundary.

The [ChatGPT developer mode and full MCP connectors guidance](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt-beta)
may change as account features roll out. Re-verify it at implementation time;
this runbook intentionally makes no claim that a personal account currently
supports every feature described there.

## Stop conditions

Stop and remove the connection if a tool asks for Fiverr credentials, returns
session material, writes canonical state without an explicit local approval,
cannot identify its database, bypasses the revision check, or causes an
unexpected network request. Rotate any exposed credential through the real
provider immediately and preserve only a redacted incident note.
