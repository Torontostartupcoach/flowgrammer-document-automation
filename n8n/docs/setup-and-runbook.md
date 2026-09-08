# Setup and runbook

Last tested 8 September 2026. Offline only. No live n8n import was performed.

## Prerequisites

- n8n Cloud or a self-hosted instance you already operate. This pack does not install n8n.
- A named reviewer who can copy a resume URL from a workflow item
- Fictional or approved labelled-text JSON only
- Placeholder credentials created in n8n Credentials, never in JSON

## Load the prepared JSON

1. Load `workflows/flowgrammer-document-processing.json`.
2. Load `workflows/flowgrammer-document-processing-error.json`.
3. Open the starter → Settings → Error workflow → choose the error workflow.
4. Keep both workflows inactive until a reviewer exists.
5. Manual Trigger → `Manual Fixture Input` (Edit Fields) supplies editable labelled-text JSON: `raw_text`, `filename`, `mime_type`, `source_system`. pinData stays empty. Webhook POST `fg-document-intake` with the same JSON shape.
6. Raw body is off. Binary files, PDFs, and images are not the default path. They fail as `unsupported_type` or `missing_raw_text`. Add authentication in the n8n UI. Do not commit that value.

## Manual reviewer handoff

Exact operator action:

1. Run the workflow on labelled-text JSON until `Prepare Reviewer Handoff`.
2. Open that item. Copy `review_handoff.resume_url`. That value is `$execution.resumeUrl` from the same execution.
3. Send the URL through a private channel you already use. The prepared JSON does not email, Slack, or otherwise transmit the URL.
4. POST `decision=approve` or `decision=reject` as a query string or JSON body. Wait `httpMethod` is POST.
5. If nobody POSTs a decision and the 24-hour wait limit resumes automatically, `Apply Review Decision` sets `review.status=timed_out`, `status=pending_review`, and destination attempts stay 0. Only an explicit `decision=reject` rejects.

Wait resume in this JSON has no authentication. Do not treat that URL as a production approval endpoint. Preferred later swap: Slack Message Send and Wait for Response, Approval, with Credentials. Slack Approvals need public HTTPS and a Slack Signature Secret stored in Credentials.

Official docs: waits under 65 seconds stay in-process. This starter uses a 24-hour limit, so assume a durable wait. Partial executions change `$execution.resumeUrl`. The handoff node must run in the same execution as Wait.

The live Wait webhook item shape (`query` / `body` / binary) is unproven without a live import. `Apply Review Decision` reads query and body and keeps the original record from `Prepare Reviewer Handoff`. That merge is specified, not live-tested.

## Duplicate store

The starter Code nodes use `$getWorkflowStaticData('global')` as a demo seen-hash map only.

Official n8n `getWorkflowStaticData` docs (accessed 2026-09-08): static data is unavailable when testing workflows; the workflow must be published and called by a trigger or webhook to save static data; the feature may behave unreliably under high-frequency executions. Data tables are the documented alternative that keep data in test executions.

Therefore: the offline harness proves the duplicate case. Do not claim the duplicate case can be proven across separate Manual Trigger runs. Live n8n duplicate persistence must be tested through the active production webhook or after swapping in Data Table, Postgres, or Redis. Do not use workflow static data as a production recommendation.

https://docs.n8n.io/build/code-in-n8n/cookbook/built-in-methods-and-variables-examples/getworkflowstaticdata/

## Hashing

SHA-256 of `raw_text` and of the idempotency material uses the official Crypto node (`action=hash`, `type=SHA256`, `encoding=hex`). Code nodes do not `require('crypto')`. No `NODE_FUNCTION_ALLOW_BUILTIN=crypto` setting is required for the prepared default.

## Destination

Default: Code FakeERP across two nodes, `Attempt Draft Write` and `Retry Draft Write`, sharing one stored draft map and the same idempotency key:

`sha256(source_sha256 + ":" + document_type + ":" + (document_number or "none"))`

The timeout fixture `INV-TP-2405` takes the true branch of `Ambiguous Timeout?` after the first write. The retry node looks up the same key and does not increment writes.

Send that value as `Idempotency-Key` if you later enable the disabled HTTP Request node. The placeholder URL is `https://example.invalid/fake-erp/drafts`. Replace it only with a draft endpoint. Never point it at payment, refund, or force-post APIs.

## Binary data and queue mode

These limits matter when you later add a binary adapter. They do not make PDF or image intake part of the default.

- Default binary mode keeps data in memory and can crash on large files.
- `N8N_DEFAULT_BINARY_DATA_MODE` accepts `default`, `filesystem`, `s3`, `azure`, `database`.
- Queue mode does not support filesystem binary storage. Use database or S3/azure. Main and workers must share the encryption key and the storage backend.

Official pages, accessed 2026-09-08:

- https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/handle-binary-data/
- https://docs.n8n.io/hosting/scaling/queue-mode/
- https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/binary-data/

## Execution retention

When pruning is enabled, official defaults include `EXECUTIONS_DATA_MAX_AGE` 336 hours and `EXECUTIONS_DATA_PRUNE_MAX_COUNT` 10000. Waiting, new, and running executions are not pruned. Annotated executions are never pruned.

https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/manage-execution-data/

Waiting handoffs therefore survive default prune. Finished executions and their binaries may not. Keep audit rows in Postgres if you need a durable trail.

## Extraction adapters

| Adapter | When to use | In default JSON |
|---|---|---|
| Labelled-text Code | Five fixture cases; JSON `raw_text` | Yes |
| Extract From File | Text-layer PDF or other supported binaries | Documented swap |
| HTTP Request to Document AI / Textract / Azure DI | Scan OCR or vendor IDP | Documented swap |
| Anthropic or Gemini Analyze Document | Paid document/image analysis | Documented swap |
| Information Extractor | Structured fields from already-extracted text | Documented swap |

Extract From File is not scan OCR. LLM and vendor adapters send bytes off the instance.

## Verification

Offline, from this folder:

```text
python3 tests/validate_workflows.py
python3 tests/test_wait_resume_contract.py
python3 tests/test_wait_timeout_path.py
python3 tests/test_manual_fixture_input.py
python3 tests/run_offline_harness.py
python3 tests/test_idempotency.py
```

After a future authorized live import, record the n8n version, Cloud or self-host, the five-case outcome, and the Wait resume item shape. Until that record exists, do not claim live behaviour.
