# Flowgrammer Document Automation

Shared starters for Flowgrammer document-automation work. This repository
is being prepared locally. It is still private. GitHub Pages is not enabled.
Nothing here is a live import, a live download, or a published site.

Canonical guide (site route, not a GitHub link):
https://flowgrammer.ca/insights/n8n-document-processing-workflow

## Current pack

**n8n Document Processing Starter v0.1.1** lives in [`n8n/`](n8n/).

It is a prepared n8n workflow pair for labelled-text document orchestration:
intake, MIME and size checks, official Crypto SHA-256 hashing, a labelled-text
extraction adapter, field and total checks, a manual reviewer handoff that
exposes `$execution.resumeUrl` before Wait, a mock draft-only destination
with two attempt nodes, append-only audit events, and a separate error
workflow.

Read [`n8n/README.md`](n8n/README.md) for setup, fixtures, and operator
caveats. The n8n folder is the pack. This root README is the repository map.

## Limits that still hold

- Default intake is labelled-text JSON only. PDF and image binaries fail as
  `unsupported_type`. That is not an OCR product.
- Offline Python tests prove the five labelled-text fixture outcomes. They
  do not prove Cloud, self-host, Slack Approvals, Extract From File, or OCR.
- Live n8n import is untested on this machine. No n8n package is installed
  here. CI on GitHub-hosted runners installs n8n 2.37.11 into a temporary
  home and runs server-CLI import for both workflow JSON files. Until that
  job is recorded green after a push, do not claim a proven live import.
- The live Wait resume item shape is unproven without a recorded import.
- Destination writes are mock drafts. This pack does not pay anyone or post
  accounting entries.

## Later folders

These names are reserved. They are not in the tree yet. Do not invent live
assets or URLs for them.

| Slot | Later use |
| --- | --- |
| `invoice/` | Invoice-specific packs, not this n8n starter |
| `power-automate/` | Power Automate variants |
| `quickbooks/` | QuickBooks-connected variants |
| app-specific folders | Vendor or product adapters when they exist |

## Verify without installing n8n

No extra Python packages are required.

```text
export PYTHONDONTWRITEBYTECODE=1
python3 n8n/tests/validate_workflows.py
python3 n8n/tests/test_wait_resume_contract.py
python3 n8n/tests/test_wait_timeout_path.py
python3 n8n/tests/test_manual_fixture_input.py
python3 n8n/tests/run_offline_harness.py
python3 n8n/tests/test_idempotency.py
```

Do not run `n8n/tests/build_workflows.py` or
`n8n/tests/build_release_archive.py` as tests.

CI also runs the official n8n server CLI against a temporary runner database:

```text
n8n import:workflow --input=n8n/workflows/flowgrammer-document-processing.json
n8n import:workflow --input=n8n/workflows/flowgrammer-document-processing-error.json
```

Those two commands run only on GitHub-hosted runners. They must exit zero.
They do not publish, activate, or call any endpoint. See
[`.github/workflows/validate-n8n.yml`](.github/workflows/validate-n8n.yml).

## Pages

A small landing page is in [`docs/`](docs/). Codex must enable GitHub Pages
before that folder is a public site. See [`docs/ENABLE-PAGES.md`](docs/ENABLE-PAGES.md).

## License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
