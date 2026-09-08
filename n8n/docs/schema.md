# Normalized document record

Minimum shape after the Code nodes run. Invoice test-pack aliases map `invoice_no` to `document_number`.

```json
{
  "document_id": "uuid-or-execution-id",
  "document_type": "invoice",
  "source_system": "webhook",
  "source_sha256": "hex",
  "filename": "01-clean-invoice.txt",
  "mime_type": "text/plain",
  "byte_size": 0,
  "received_at": "2026-09-08T00:00:00Z",
  "extraction": {
    "vendor": "Ridgemont Industrial Supply Co",
    "document_number": "INV-TP-2401",
    "invoice_no": "INV-TP-2401",
    "date": "2026-09-08",
    "currency": "CAD",
    "subtotal": 400.0,
    "tax": 52.0,
    "total": 452.0,
    "line_items": [],
    "raw_text": null,
    "model_confidence": null,
    "adapter": "labelled_text_fixture"
  },
  "validation": {
    "ok": true,
    "exception_codes": [],
    "field_errors": []
  },
  "duplicate": { "is_duplicate": false, "matched_on": null },
  "review": { "status": "pending", "actor": null, "decided_at": null },
  "destination": { "status": "not_attempted", "draft_id": null, "attempts": 0, "writes": 0 },
  "idempotency_key": "hex",
  "audit_event_ids": ["received", "validated", "review_requested"]
}
```

Accepted default intake is labelled-text JSON: `raw_text` required; optional `filename`, `mime_type`, `source_system`. Default MIME is `text/plain`. PDF and image binaries are `unsupported_type` in this default.

Idempotency key: SHA-256 of `source_sha256 + ":" + document_type + ":" + (document_number or "none")`, hashed by the official Crypto node.

`review_handoff.resume_url` is `$execution.resumeUrl` written before Wait. An empty automatic resume is `review.status=timed_out` and `status=pending_review`. The live Wait item shape is unproven without import.
