# Seller OS v3: official marketplace and MCP constraints

**Research date:** 2026-08-12  
**Scope:** primary, first-party sources only; no Fiverr login, scraping, credential use, or deployment.  
**Purpose:** turn current platform rules into constraints for a local, evidence-led Gig and proposal studio.

## Executive conclusion

V3 should be an evidence-led drafting and review studio, not an autopublisher or marketplace scraper. The local SQLite/stdio core is a good fit: it can retain structured facts, provenance, drafts, risk findings, and explicit approvals while keeping Fiverr actions human-controlled.

The first useful product surface is a “Gig readiness packet” and “brief response packet” that produces drafts plus evidence and policy checks. It should never imply that a draft was published, that a client was contacted, or that a marketplace result is guaranteed.

## Fiverr constraints that shape the domain

### Gig structure is bounded and reviewable

Fiverr’s [Creating a Gig](https://help.fiverr.com/hc/en-us/articles/360010451397-Creating-a-Gig) guide describes a Gig as title, category/subcategory, tags, packages, description/FAQ, requirements, and gallery. Titles should be specific and client-focused; category selection is effectively durable after publication; there are up to three packages, each with delivery time, revisions, and USD price; descriptions are limited to 1,200 characters; requirements can be marked required; and publishing requires compliant gallery media and account verification.

**V3 implications:** model each field separately, store character/count validations, make category and package decisions explicit, and provide a preflight report before any human copies content into Fiverr. A draft should carry `source_facts`, `assumptions`, `unknowns`, and `evidence_refs`; generated prose without support must be visibly marked as a proposal rather than a fact.

### Requirements are a data-collection contract

Fiverr’s [buyer requirements guidance](https://help.fiverr.com/hc/en-us/articles/360011079098-How-to-effectively-use-buyer-requirements) says requirements collect what is needed to complete the order and should be designed around the actual service. The [Gig creation guide](https://help.fiverr.com/hc/en-us/articles/360010451397-Creating-a-Gig) recommends collecting relevant project details up front and gives development-project examples such as goal, audience, existing content, references, timeline, and hosting credentials when necessary.

**V3 implications:** requirements should be typed as `required`, `optional`, or `conditional`, with a reason and safe handling instruction. The intake layer should reject or redact secrets, avoid retaining raw buyer text by default, and distinguish “needed to scope” from “needed to execute.” Credentials should never be requested in a generic template; if a real order requires access, the studio should flag a human security decision instead of asking the model to handle it.

### Claims must be truthful and service-specific

Fiverr’s [account activation guidance](https://help.fiverr.com/hc/en-us/articles/360050063113-Creating-your-Fiverr-account) requires truthful, accurate training, work-experience, and skills information. Fiverr’s [Gig best practices](https://help.fiverr.com/hc/en-us/articles/360010452317-Gigs-best-practices) recommends representative images, realistic delivery times, and consistent service positioning. Its [prohibited-services policy](https://help.fiverr.com/hc/en-us/articles/49174165608593-Prohibited-services-on-Fiverr) disallows misleading guarantees, unauthorized access, privacy violations, scraping personal data, and automation that violates another platform’s terms.

**V3 implications:** every profile/Gig claim needs a support level: `verified`, `user_asserted`, `inferred`, or `unverified`. The writer must not upgrade an inference into a credential, years-of-experience claim, certification, guarantee, or portfolio result. “Python automation,” “local MCP integration,” or “workflow tooling” should only appear at the strength supported by local project evidence and user confirmation. A policy scanner should flag guarantees, “guaranteed results,” unauthorized-access language, scraping, credential collection, fake engagement, and platform-terms circumvention.

### Off-platform contact and deceptive promotion are hard stops

Fiverr’s [promotion guidance](https://help.fiverr.com/hc/en-us/articles/360010490438-Promoting-your-Gigs-outside-of-Fiverr) says external promotion should point traffic to Fiverr and must not share personal contact information. [Gig violations guidance](https://help.fiverr.com/hc/en-us/articles/37555045126289-Gig-violations) identifies external contact/payment details and URLs in Gig content or images as violations. Fiverr also prohibits fake reviews, fake engagement, impersonation, and deceptive AI content in its [community standards](https://help.fiverr.com/hc/en-us/articles/37554441398929-Our-Community-Standards).

**V3 implications:** run a final content scan across title, description, FAQ, requirements, tags, image text, and proposal drafts. Treat contact details, alternate payment instructions, off-platform CTAs, fabricated testimonials, and fabricated portfolio outcomes as blocking findings requiring human correction—not as rewrite suggestions the model can silently “fix.”

### Briefs are time-sensitive and fit-based

Fiverr’s [Personalized offers (Briefs)](https://help.fiverr.com/hc/en-us/articles/4415608857745-Personalized-offers-Briefs-for-freelancers) documentation says briefs are matched to skills, experience, pricing, and profession; sellers can create an offer, decline, or ask questions; and a brief is available for response within 72 hours. The article also warns against including sensitive information in brief requests.

**V3 implications:** represent a brief with `received_at`, `expires_at`, fit dimensions, unanswered questions, and a response status. Provide a “fit / missing evidence / risk / next question” view before drafting. The studio must not claim access to or freshness of a Fiverr Brief unless the user imported it manually or through an explicitly authorized future connector.

## OpenAI/MCP constraints

OpenAI’s [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) supports private MCP servers without exposing them to the public internet. It uses an outbound client that reaches OpenAI and forwards queued MCP work to the local server; it is for supported OpenAI products and private connections, not public plugin distribution. OpenAI’s [MCP apps guidance](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt-beta) says access and write support vary by plan/workspace, custom app changes may require a fresh review, and users/admins are responsible for vetting untrusted servers and prompt-injection risk.

**V3 implications:** keep stdio as the canonical transport and treat a tunnel as an adapter/deployment concern. Begin with read-heavy tools and synthetic state. Separate proposal generation from approval and external action. Publish an explicit tool manifest and risk classification; changing tool descriptions or adding write tools should trigger a new review. Never put Fiverr credentials or raw buyer messages into MCP tool descriptions, logs, or test fixtures.

The [MCP authorization specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) is relevant only when a future remote HTTP server is introduced. V3 should not invent bearer-token auth for local stdio or assume a public URL is safe. Any future remote endpoint needs standards-based authorization, redirect/origin validation, secret rotation, and an explicit threat-model review.

## Recommended v3 artifacts

1. **Evidence ledger:** atomic claims, source path, provenance type, user confirmation, last verified date, and permitted wording.
2. **Gig draft packet:** bounded fields, package matrix, requirements contract, FAQ, media checklist, and policy findings.
3. **Brief response packet:** imported brief metadata, fit score with explanations, missing questions, draft response, and expiry status.
4. **Preflight evaluator:** deterministic length/count checks, unsupported-claim detection, prohibited-service terms, contact/payment leakage, and evidence coverage.
5. **Approval workflow:** draft → review → approved-for-copying; no publish/send/browser action in the core.
6. **Audit trail:** record source imports, evidence confirmations, draft revisions, findings, and approvals without retaining sensitive raw text.

## Currentness and uncertainty

These pages were retrieved on 2026-08-12. Fiverr explicitly says prohibited-service examples and marketplace rules may change, and OpenAI states MCP/app functionality is rolling out and may change. The studio should therefore version its policy rules, retain source URLs and retrieval dates, and label output as “review against current Fiverr rules before publishing.” These sources describe platform capabilities and constraints; they do not establish that `@chotaku` has any particular public profile, Gig, credential, ranking, or eligibility.

