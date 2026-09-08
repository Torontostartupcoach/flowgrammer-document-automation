#!/usr/bin/env python3
"""Regression: 24-hour Wait auto-resume must not reject or write a draft."""

from __future__ import annotations

import sys
from pathlib import Path

from document_processing import (
    DuplicateStore,
    FakeERP,
    classify_resume_decision,
    process_document,
    validate_file,
)
from validate_workflows import (
    MAIN,
    WAIT_NAME,
    code_of,
    load,
    node_by_name,
    outgoing_branches,
)

ROOT = Path(__file__).resolve().parents[1]


def apply_review_n8n_shape(stored: dict, incoming: dict) -> dict:
    """Mirror Apply Review Decision: empty automatic resume is timed_out."""
    rec = dict(stored)
    query = incoming.get("query") or {}
    body = incoming.get("body") if isinstance(incoming.get("body"), dict) else {}
    raw = query.get("decision") or body.get("decision") or incoming.get("decision")
    review_status = classify_resume_decision(None if raw is None else str(raw))
    rec["review"] = {"status": review_status, "actor": "wait-limit" if review_status == "timed_out" else "manual-handoff"}
    rec["approved"] = review_status == "approved"
    rec["explicit_reject"] = review_status == "rejected"
    rec["destination"] = rec.get("destination") or {"status": "not_attempted", "draft_id": None, "attempts": 0, "writes": 0}
    if review_status == "rejected":
        rec["status"] = "rejected"
    elif review_status == "timed_out":
        rec["status"] = "pending_review"
        rec["destination"]["attempts"] = 0
        rec["destination"]["status"] = "not_attempted"
    return rec


def main() -> int:
    errors: list[str] = []
    stored = {
        "status": "pending_review",
        "destination": {"status": "not_attempted", "draft_id": None, "attempts": 0, "writes": 0},
        "validation": {"ok": True, "exception_codes": [], "field_errors": []},
    }

    empty = apply_review_n8n_shape(stored, {})
    if empty["review"]["status"] != "timed_out" or empty["status"] != "pending_review":
        errors.append("empty resume must be timed_out + pending_review")
    if empty["destination"]["attempts"] != 0 or empty["approved"] or empty["explicit_reject"]:
        errors.append("empty resume must not approve, reject, or increment destination attempts")

    timeout_word = apply_review_n8n_shape(stored, {"query": {"decision": "timeout"}})
    if timeout_word["review"]["status"] != "timed_out" or timeout_word["status"] != "pending_review":
        errors.append("decision=timeout must stay pending_review")

    reject = apply_review_n8n_shape(stored, {"body": {"decision": "reject"}})
    if reject["review"]["status"] != "rejected" or reject["status"] != "rejected":
        errors.append("explicit reject must reject")

    approve = apply_review_n8n_shape(stored, {"query": {"decision": "approve"}})
    if not approve["approved"] or approve["status"] == "rejected":
        errors.append("explicit approve must not reject or time out")

    unknown = apply_review_n8n_shape(stored, {"decision": "maybe"})
    if unknown["status"] != "pending_review" or unknown["explicit_reject"]:
        errors.append("unknown decision must not reject")

    text = (ROOT / "fixtures" / "01-clean-invoice.txt").read_text(encoding="utf-8")
    pending = process_document("timeout-path", text, DuplicateStore(), FakeERP(), reviewer=None)
    timed = process_document(
        "timeout-path-empty",
        text,
        DuplicateStore(),
        FakeERP(),
        reviewer=lambda _decision: "",
    )
    if timed.status != "pending_review" or timed.destination_attempts != 0:
        errors.append(
            f"Python empty-reviewer path: status={timed.status} attempts={timed.destination_attempts}"
        )
    if pending.destination_attempts != 0:
        errors.append("pending record must have zero destination attempts before review")

    if validate_file("scan.pdf", "application/pdf", 1200) != ["unsupported_type"]:
        errors.append("PDF MIME must be unsupported in the labelled-text default")
    if validate_file("scan.png", "image/png", 800) != ["unsupported_type"]:
        errors.append("image MIME must be unsupported in the labelled-text default")
    if validate_file("invoice.txt", "text/plain", 80):
        errors.append("text/plain .txt must remain the accepted labelled-text shape")

    workflow = load(MAIN)
    wait = node_by_name(workflow, WAIT_NAME)
    if (wait.get("parameters") or {}).get("httpMethod") != "POST":
        errors.append("Wait httpMethod must be explicit POST")
    apply_js = code_of(workflow, "Apply Review Decision")
    if "decision === 'reject'" not in apply_js:
        errors.append("Apply Review JS must require explicit reject")
    if "else reviewStatus = 'timed_out'" not in apply_js and "reviewStatus = 'timed_out'" not in apply_js:
        errors.append("Apply Review JS must default empty resume to timed_out")
    if "else if (!rec.approved)" in apply_js:
        errors.append("Apply Review JS still maps non-approve to rejected")
    branches = outgoing_branches(workflow)
    approve_false = (branches.get("Approved?") or [[], []])[1]
    reject_false = (branches.get("Explicit Reject?") or [[], []])[1]
    if "Attempt Draft Write" in approve_false or "Attempt Draft Write" in reject_false:
        errors.append("timeout path must not reach Attempt Draft Write")
    if "Record Review Timeout" not in reject_false:
        errors.append("automatic timeout must use Record Review Timeout")
    if "Record Rejection" in reject_false:
        errors.append("automatic timeout must not record a rejection")

    if errors:
        print("FAIL: wait timeout path")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: empty/automatic Wait resume is timed_out, pending_review, zero destination attempts")
    print("NOTE: live Wait auto-resume item shape remains unproven without a live n8n import.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
