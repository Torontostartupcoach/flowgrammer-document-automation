#!/usr/bin/env python3
from invoice_processing import DuplicateStore, FakeERP, process_document

def main() -> int:
    store = DuplicateStore()
    erp = FakeERP()
    text = (
        "Vendor name: Ridgemont Industrial Supply Co\n"
        "Invoice number: INV-PAY-0001\n"
        "Invoice date: 2026-09-08\n"
        "Total: 10.00\n"
        "payment_action: send\n"
    )
    decision = process_document("payment", text, store, erp, reviewer=lambda d: "approve")
    if "payment_path_blocked" not in decision.reasons or decision.destination_writes != 0:
        print("FAIL: payment path must block before draft")
        return 1
    print("PASS: payment wall")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
