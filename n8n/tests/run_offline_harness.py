#!/usr/bin/env python3
"""Run the five labelled-text fixtures through the offline control engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from document_processing import (
    DuplicateStore,
    FakeERP,
    TIMEOUT_INVOICE_NO,
    apply_review,
    extract_labelled_invoice,
    extraction_for_expected,
    process_document,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
EXPECTED = ROOT / "expected"


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def compare_extraction(actual: dict, expected: dict, case_id: str) -> list[str]:
    errors: list[str] = []
    slim = extraction_for_expected(actual)
    if slim != expected:
        errors.append(f"{case_id}: extraction mismatch")
        for key in expected:
            if slim.get(key) != expected.get(key):
                errors.append(f"  {key}: got {slim.get(key)!r} expected {expected.get(key)!r}")
    return errors


def main() -> int:
    cases = json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))["cases"]
    store = DuplicateStore()
    erp = FakeERP(timeout_after_write_for={TIMEOUT_INVOICE_NO})
    errors: list[str] = []
    results = []

    for case in cases:
        expected = json.loads((EXPECTED / case["expected_file"]).read_text(encoding="utf-8"))
        text = load_text(case["file"])
        without = process_document(case["id"], text, store, erp, reviewer=None)
        errors.extend(compare_extraction(without.extraction, expected["extraction"], case["id"]))
        wf = expected["workflow"]
        if without.status != wf["status_without_reviewer"]:
            errors.append(
                f"{case['id']}: status without reviewer {without.status} != {wf['status_without_reviewer']}"
            )
        if without.destination_attempts != wf["destination_attempts_without_reviewer"]:
            errors.append(f"{case['id']}: attempts without reviewer {without.destination_attempts}")
        if without.destination_writes != wf["destination_writes_without_reviewer"]:
            errors.append(f"{case['id']}: writes without reviewer {without.destination_writes}")
        if case["id"] == "duplicate":
            if without.review_invocations != wf.get("review_invocations", 0):
                errors.append(f"{case['id']}: review invocations {without.review_invocations}")
            if set(without.reasons) != set(wf["reasons"]):
                errors.append(f"{case['id']}: reasons {without.reasons} != {wf['reasons']}")
            results.append(without)
            continue

        pending = apply_review(without, erp, wf["simulated_review"])
        if pending.status != wf["status_after_simulated_review"]:
            errors.append(
                f"{case['id']}: status after review {pending.status} != {wf['status_after_simulated_review']}"
            )
        if pending.destination_attempts != wf["destination_attempts_after_simulated_review"]:
            errors.append(
                f"{case['id']}: attempts after review {pending.destination_attempts} != {wf['destination_attempts_after_simulated_review']}"
            )
        if pending.destination_writes != wf["destination_writes_after_simulated_review"]:
            errors.append(
                f"{case['id']}: writes after review {pending.destination_writes} != {wf['destination_writes_after_simulated_review']}"
            )
        expected_reasons = [code for code in wf["reasons"] if code != "review_rejected"]
        if set(expected_reasons) - set(pending.reasons):
            errors.append(f"{case['id']}: missing reasons {expected_reasons} in {pending.reasons}")
        results.append(pending)

    # Keep extract_labelled_invoice import used for a smoke parse.
    if extract_labelled_invoice(load_text("01-clean-invoice.txt")).get("invoice_no") != "INV-TP-2401":
        errors.append("clean fixture parser failed")

    if errors:
        print("FAIL: offline fixture harness")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS: five labelled-text fixture cases ({len(results)} decisions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
