#!/usr/bin/env python3
"""Prove timeout retry uses one write and the same idempotency key and draft id."""

from __future__ import annotations

import sys
from pathlib import Path

from document_processing import (
    DuplicateStore,
    FakeERP,
    TIMEOUT_INVOICE_NO,
    idempotency_key,
    process_document,
    sha256_text,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    text = (ROOT / "fixtures" / "05-ambiguous-destination-timeout.txt").read_text(encoding="utf-8")
    store = DuplicateStore()
    erp = FakeERP(timeout_after_write_for={TIMEOUT_INVOICE_NO})
    pending = process_document("timeout", text, store, erp, reviewer=None)
    if pending.status != "pending_review":
        print(f"FAIL: expected pending_review, got {pending.status}")
        return 1
    if pending.destination_attempts != 0:
        print("FAIL: destination called before approve")
        return 1

    expected_key = idempotency_key(sha256_text(text), "invoice", pending.extraction.get("document_number"))
    if pending.idempotency_key != expected_key:
        print("FAIL: idempotency key formula mismatch")
        return 1

    writes_before = erp.writes
    draft_ids = []
    last_error = None
    for _ in range(2):
        pending.destination_attempts += 1
        try:
            result = erp.post(
                {"invoice_no": pending.extraction.get("document_number")},
                pending.idempotency_key,
            )
            draft_ids.append(result["id"])
            last_error = None
        except TimeoutError as exc:
            last_error = str(exc)
            if pending.idempotency_key in erp.seen_keys:
                draft_ids.append(erp.seen_keys[pending.idempotency_key])
    pending.destination_writes = erp.writes - writes_before
    if pending.destination_attempts < 2:
        print(f"FAIL: expected at least two attempts, got {pending.destination_attempts}")
        return 1
    if pending.destination_writes != 1:
        print(f"FAIL: expected one write, got {pending.destination_writes}")
        return 1
    if len(set(draft_ids)) != 1:
        print(f"FAIL: draft ids diverged {draft_ids}")
        return 1
    if last_error is None and pending.destination_attempts < 2:
        print("FAIL: timeout path did not surface a lost response")
        return 1
    print(
        f"PASS: timeout idempotency attempts={pending.destination_attempts} "
        f"writes={pending.destination_writes} draft_id={draft_ids[0]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
