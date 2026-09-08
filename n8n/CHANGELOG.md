# Changelog

## 0.1.1 - 2026-09-08

- Wait v1.1 timeout parameters are top-level: `limitWaitTime`, `limitType`, `resumeAmount`, `resumeUnit`
- Wait `httpMethod` is explicit POST
- `Prepare Reviewer Handoff` exposes `$execution.resumeUrl` before Wait
- Empty or automatic Wait resume maps to `timed_out` / `pending_review` / zero destination attempts; only `decision=reject` rejects
- Destination retry is two Code nodes (`Attempt Draft Write`, `Retry Draft Write`) with one stored write
- Hashing uses official Crypto nodes; Code nodes do not `require('crypto')`
- Default intake is labelled-text JSON (`text/plain`); PDF and image binaries are unsupported in the default
- Validators check parameter shape and graph behaviour, not only node names
- Language: prepared n8n workflow JSON. Live import remains a blocker
- Manual Trigger feeds an Edit Fields fixture node with labelled-text JSON; pinData stays empty
- Duplicate persistence: offline harness proves it; static data is not a production store and cannot be proven across Manual Trigger runs

## 0.1.0 - 2026-09-08

- Original starter and error workflows for document processing controls
- Offline Python harness for the five labelled-text invoice fixtures
- SHA-256 and optional vendor-plus-number duplicate stop
- Mock draft-only destination
- Documentation for binary data, queue mode, Data Table limits, and execution retention
- No live n8n import. That remains a release blocker.
