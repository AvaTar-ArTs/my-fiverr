# Security boundaries

Version 1 is local-only. It does not expose an HTTP service, tunnel, or remote
control surface.

Version 1 performs no Fiverr API calls or browser actions. Fiverr interaction is
outside this initial package boundary.

## Local state

The state directory is intended to be owner-only: directory permissions should
be `0700` and files should be `0600` where the operating system supports those
modes. `FIVERR_SELLER_OS_STATE_DIR` is available when the default per-user
location is unsuitable. Resolving that path never creates or changes it; a
future state-initialization command must set restrictive permissions explicitly.

## Secrets and logs

Do not store credentials, API keys, browser cookies, browser profiles, or other
session material in this repository or local Seller OS state. The `private/`
directory holds deployment templates and runbooks only; it is not a credential
vault.

Logs and audit entries must redact secrets and sensitive values, including
authorization headers, tokens, passwords, cookies, and connection strings.
Run an appropriate secret scan before every commit, and remove any discovered
secret from the working tree and git history before sharing or pushing it.
