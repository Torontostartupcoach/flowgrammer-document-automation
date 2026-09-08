# Release readiness

## Passed offline

- Prepared workflow JSON and error workflow JSON
- Graph includes labelled-text JSON intake, validation, official Crypto hash, duplicate stop, extraction adapter, schema checks, pre-Wait resume URL handoff, Wait with top-level 24-hour limit and explicit POST, two destination attempt nodes, audit
- Five labelled-text fixture outcomes. Duplicate stop is proven by the offline harness, not by separate Manual Trigger runs.
- Timeout idempotency: two distinct destination nodes, one write, same draft id
- Empty Wait resume: `timed_out`, `pending_review`, zero destination attempts
- Credential objects absent; pinData empty; template 17806 absent; `require('crypto')` absent
- MIT licence and NOTICE

## Release blockers

1. Live n8n import and execution are untested. No n8n runtime is installed in this workspace.
2. The live Wait webhook resume item shape (`query` / `body` / binary) is unproven. Do not assert it.
3. The `flowgrammer-document-automation` GitHub repository does not exist. Do not publish a repository URL.
4. Slack Approvals, Extract From File, Data Table, queue mode, and Cloud behaviour are untested.
5. OCR is not measured.
6. Codex must replace the article GitHub CTA placeholder only after the `n8n/` folder is live.

## Do not claim

- That `$getWorkflowStaticData` persists across Manual Trigger runs
- Tested Cloud or self-host behaviour
- Importable-and-verified live workflows
- OCR accuracy
- A live download or GitHub release
- Payment or posted accounting behaviour
- A public unauthenticated production approval endpoint
- That Code-node `require('crypto')` is portable without `NODE_FUNCTION_ALLOW_BUILTIN`
