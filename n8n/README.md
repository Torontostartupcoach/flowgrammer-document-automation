# Flowgrammer n8n Document Processing Starter

Version 0.1.1. Last tested 8 September 2026.

Original Flowgrammer n8n starter for document orchestration. It shows intake of labelled-text JSON, MIME and size checks, official Crypto SHA-256 hashing, a labelled-text extraction adapter, deterministic field and total checks, a manual reviewer handoff that exposes `$execution.resumeUrl` before Wait, a mock draft-only destination with two distinct attempt nodes, append-only audit events, and a separate error workflow.

This folder is the intended `n8n/` tree for a later `flowgrammer-document-automation` repository. That repository does not exist yet. Do not treat any GitHub URL as live.

Canonical article (site route, not a GitHub link): https://flowgrammer.ca/insights/n8n-document-processing-workflow

## What this pack is

- Two prepared n8n workflow JSON files written from scratch
- An offline Python harness that proves the five labelled-text cases
- Setup notes for later binary adapters, queue mode, Data Tables, and execution retention
- Fictional Cedar & Quay Fabrication Ltd fixtures

It is not an OCR product. It is not an invoice-automation accounting pack. It does not pay anyone. Live n8n import is untested and remains a release blocker.

## Accepted default input

The prepared default consumes labelled-text JSON only:

```json
{
  "raw_text": "Vendor name: ...",
  "filename": "01-clean-invoice.txt",
  "mime_type": "text/plain",
  "source_system": "labelled_text_json"
}
```

`raw_text` is required. `filename`, `mime_type`, and `source_system` are optional and default to `fixture.txt`, `text/plain`, and `labelled_text_json`.

The default does not read webhook Raw body, binary files, PDFs, or images. A PDF or image MIME type fails as `unsupported_type`. Swap in Extract From File later if you want a text-layer PDF path. That swap is documented, not included as the default.

## Labelled-text fixtures do not measure OCR

The five files in `fixtures/` are reused from Flowgrammer's published Invoice Processing Test Pack. They are labelled text. They prove workflow gates. They do not prove Extract From File on a text-layer PDF, and they do not prove scan OCR.

## Quick start without n8n

No n8n runtime, Node packages, Docker images, or extra Python packages are required for the documented test.

```text
python3 tests/validate_workflows.py
python3 tests/test_wait_resume_contract.py
python3 tests/test_wait_timeout_path.py
python3 tests/test_manual_fixture_input.py
python3 tests/run_offline_harness.py
python3 tests/test_idempotency.py
```

Expected: all five commands print PASS. Live n8n import and execution remain a release blocker. This pack does not claim tested Cloud or self-host behaviour. The live Wait resume item shape is unproven.

## Load the prepared JSON when you have n8n

1. Load `workflows/flowgrammer-document-processing.json`.
2. Load `workflows/flowgrammer-document-processing-error.json`.
3. In the starter workflow Settings, set Error Workflow to the error workflow.
4. Leave the starter inactive until credentials and a reviewer exist.
5. Manual Trigger runs `Manual Fixture Input` (Edit Fields) first. That node ships editable `raw_text`, `filename`, `mime_type`, and `source_system`. pinData stays empty. Webhook POST `fg-document-intake` with the same JSON shape. Raw body is off.
6. `Prepare Reviewer Handoff` writes `review_handoff.resume_url` from `$execution.resumeUrl`. Copy that URL and POST `decision=approve` or `decision=reject` through a private channel. The workflow does not email or Slack the URL. Wait resume has no authentication in this JSON. That is not a production approval endpoint.
7. If the 24-hour wait limit resumes with no decision, status stays `pending_review` and the destination is not called.
8. Destination is Code FakeERP with `Attempt Draft Write` and `Retry Draft Write`. An optional HTTP Request node points at `https://example.invalid/fake-erp/drafts` and stays disabled.

## Five cases

| Case | File | Without reviewer | After simulated review |
|---|---|---|---|
| Clean | `01-clean-invoice.txt` | `pending_review`, 0 writes | approve → one draft |
| Duplicate | `02-duplicate-invoice.txt` | `duplicate`, 0 review, 0 writes (offline harness) | no review |
| Missing number | `03-missing-invoice-number.txt` | `missing_invoice_no`, 0 writes | reject → no draft |
| Conflicting total | `04-conflicting-total.txt` | `conflicting_total`, 0 writes | reject → no draft |
| Timeout | `05-ambiguous-destination-timeout.txt` | `pending_review`, 0 writes | approve → two destination nodes, writes 1, same draft id |

Every non-duplicate stays pending until an explicit approve. A duplicate never opens review and never calls the destination. An empty Wait resume is a timeout, not a reject.

The offline harness proves the duplicate case. Official n8n docs say `$getWorkflowStaticData` is unavailable in manual testing and only saves when a published workflow is called by a trigger or webhook. It may be unreliable at high frequency. Do not claim the duplicate case can be proven across separate Manual Trigger runs. Live n8n duplicate persistence must be tested through the active production webhook or after swapping in Data Table, Postgres, or Redis. Workflow static data is a demo map, not a production recommendation.

## What this pack will not do

- Copy community template 17806 or any unclear-licence workflow JSON
- Auto-release a draft because a model confidence score is high
- Create a payment, refund, or posted accounting entry
- Store live credentials, resume URLs, or customer files
- Measure OCR accuracy
- Claim live execution, a public unauthenticated production approval flow, or hashing that needs `NODE_FUNCTION_ALLOW_BUILTIN`

## Official operator caveats

- Default binary data mode keeps files in memory and can crash on large PDFs. Set `N8N_DEFAULT_BINARY_DATA_MODE` to `filesystem`, `database`, `s3`, or `azure` as appropriate when you later add a binary adapter.
- Queue mode does not support filesystem binary storage. Use database or external object storage.
- Data tables default to 200 MiB for the whole instance. Official n8n docs prefer them over static data for persistence between executions. They are still a demo store here, not a compliance archive.
- Execution pruning defaults include a 336-hour age and a 10000-count cap when pruning is on. Waiting, new, and running executions are not pruned. Annotated executions are never pruned.
- Official Wait docs require `$execution.resumeUrl` to be referenced in the same execution before the Wait node. Partial executions change the URL.
- Hashing uses the official Crypto node. Code nodes do not `require('crypto')`.

Sources for those limits are official n8n docs accessed 8 September 2026. They are listed in `docs/setup-and-runbook.md`.

## License

MIT. See LICENSE and NOTICE.md.
