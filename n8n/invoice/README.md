# Flowgrammer n8n Invoice Processing Workflow

Version 0.1.0. Last tested 9 September 2026.

Original Flowgrammer invoice specialization of the document-processing control plane. It hashes source bytes with the official Crypto node, blocks payment markers, stops a duplicate on SHA-256 or vendor plus invoice number, waits for an explicit Wait approve, and writes one draft. A timeout retries the same idempotency key with write_count=1.

Slack Approvals is the preferred later production swap. It is not in this default JSON so exported credentials cannot ship.

This package is published in the n8n/invoice tree of the public flowgrammer-document-automation repository.

Canonical article: https://flowgrammer.ca/insights/n8n-invoice-automation

Extract From File is not OCR. Labelled-text fixtures do not measure OCR. Community template 17806 is reference only. Do not copy it.

## Quick start without n8n

```text
python3 tests/validate_workflows.py
python3 tests/test_payment_wall.py
python3 tests/run_offline_harness.py
```

## Human decisions

A named person approves or rejects every non-duplicate through Wait. A person confirms vendor and tax. A person never pays from this workflow.

## Known limitations

The offline harness is not a live n8n Cloud run. Wait resume item shape is unproven without a live import. Credentials stay in n8n Credentials. Data tables are a demo store.
