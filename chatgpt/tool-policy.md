# ChatGPT bridge tool policy

This directory is a policy and verification layer over the existing local
Seller OS MCP. It is not an MCP server and it does not contain a database.

## Initial read-only surface

The first proposed ChatGPT scan is limited to these reads:

- `seller_get_brief`
- `profile_get`
- `gigs_list`
- `gig_get`
- `changeset_get`
- `changesets_list`
- `projects_list`
- `project_get`

The verifier checks that these tools exist on the existing 13-tool stdio
server. The other tools remain present for local development but are not part
of the initial ChatGPT read-only policy.

## Proposal and approval boundary

`changeset_propose` may be considered in a later phase as a proposal-only
operation. `changeset_approve`, `projects_create`, and `project_transition`
remain local approval operations. ChatGPT must not approve, publish, save, or
perform any Fiverr action. A human performs local approval after reviewing a
version-checked changeset.

There is no second database: all state remains in the canonical local SQLite
store under the Seller OS state directory.

## Explicit exclusions

The bridge does not use a public HTTP listener, Cloudflare, browser
automation, FTP, Fiverr credentials, or external mutation. Do not add a token
or secret to this directory or to the MCP tool arguments.
