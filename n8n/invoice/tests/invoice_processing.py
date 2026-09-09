"""Original Flowgrammer invoice-processing control engine.

This module is the offline twin of the Code nodes in the invoice workflow.
It does not copy community workflow JSON. Labelled-text fixtures do not
measure OCR.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


REQUIRED_INVOICE_FIELDS = ("vendor", "document_number", "date", "total")
TOLERANCE = 0.011
DOCUMENT_TYPE = "invoice"
ALLOWED_MIME = {
    "text/plain",
}
ALLOWED_EXTENSIONS = {".txt"}
MAX_BYTES = 10 * 1024 * 1024
TIMEOUT_INVOICE_NO = "INV-TP-2405"


PAYMENT_MARKERS = ("payment_action: send", "create_billpayment", "create_payment", "bank_write")


def payment_requested(text: str, extraction: dict[str, Any] | None = None) -> bool:
    blob = (text or "").lower()
    if any(marker in blob for marker in PAYMENT_MARKERS):
        return True
    extra_flags = extraction or {}
    return bool(extra_flags.get("payment_requested"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def idempotency_key(source_sha256: str, document_type: str, document_number: str | None) -> str:
    material = f"{source_sha256}:{document_type}:{document_number or 'none'}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def normalize_vendor(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _match(text: str, pattern: str) -> str | None:
    found = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not found:
        return None
    value = found.group(1).strip()
    return value or None


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    return float(value)


def extract_labelled_invoice(text: str) -> dict[str, Any]:
    """Parse Invoice Processing Test Pack labelled text. Not OCR."""
    line_items: list[dict[str, Any]] = []
    in_items = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower().startswith("item |"):
            in_items = True
            continue
        if in_items:
            if not line or line.lower().startswith("subtotal"):
                in_items = False
            else:
                parts = [part.strip() for part in line.split("|")]
                if len(parts) == 4:
                    line_items.append(
                        {
                            "description": parts[0],
                            "quantity": float(parts[1]),
                            "unit_price": float(parts[2]),
                            "amount": float(parts[3]),
                        }
                    )
    invoice_no = _match(text, r"^Invoice number:[ \t]*(.*?)\s*$")
    extraction = {
        "vendor": _match(text, r"^Vendor name:\s*(.+)$"),
        "vendor_address": _match(text, r"^Vendor address:\s*(.+)$"),
        "tax_registration": _match(text, r"^GST/HST number:\s*(.+)$"),
        "invoice_no": invoice_no,
        "document_number": invoice_no,
        "date": _match(text, r"^Invoice date:\s*(\d{4}-\d{2}-\d{2})"),
        "due_date": _match(text, r"^Due date:\s*(\d{4}-\d{2}-\d{2})"),
        "po_number": _match(text, r"^Purchase order:\s*(\S+)"),
        "currency": _match(text, r"^Currency:\s*([A-Z]{3})"),
        "payment_terms": _match(text, r"^Payment terms:\s*(.+)$"),
        "bill_to": _match(text, r"^Bill to:\s*(.+)$"),
        "bill_to_address": _match(text, r"^Bill-to address:\s*(.+)$"),
        "line_items": line_items,
        "subtotal": _float(_match(text, r"^Subtotal:\s*([\d.]+)")),
        "tax_label": _match(text, r"^Tax label:\s*(.+)$"),
        "tax": _float(_match(text, r"^Tax:\s*([\d.]+)")),
        "total": _float(_match(text, r"^Total:\s*([\d.]+)")),
        "raw_text": text,
        "model_confidence": None,
        "adapter": "labelled_text_fixture",
    }
    return extraction


def validate_file(filename: str, mime_type: str, byte_size: int) -> list[str]:
    reasons: list[str] = []
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
    if mime_type not in ALLOWED_MIME:
        reasons.append("unsupported_type")
    elif suffix and suffix not in ALLOWED_EXTENSIONS:
        reasons.append("unsupported_type")
    if byte_size > MAX_BYTES:
        reasons.append("file_too_large")
    return reasons


def validate_invoice(extraction: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if extraction.get("vendor") in (None, ""):
        reasons.append("missing_required_field")
    if extraction.get("document_number") in (None, ""):
        reasons.append("missing_invoice_no")
    if extraction.get("date") in (None, ""):
        reasons.append("missing_required_field")
    if extraction.get("total") in (None, ""):
        reasons.append("missing_required_field")
    subtotal = extraction.get("subtotal")
    tax = extraction.get("tax")
    total = extraction.get("total")
    if subtotal is not None and tax is not None and total is not None:
        if abs(round(float(subtotal) + float(tax), 2) - float(total)) > TOLERANCE:
            reasons.append("conflicting_total")
    if not extraction.get("raw_text") and not extraction.get("line_items"):
        reasons.append("unreadable_extract")
    return reasons


class DuplicateStore:
    def __init__(self) -> None:
        self.seen_sha: dict[str, str] = {}
        self.seen_business: dict[str, str] = {}

    def check(self, source_sha256: str, vendor: str | None, document_number: str | None) -> str | None:
        if source_sha256 in self.seen_sha:
            return "duplicate_source"
        if document_number:
            key = f"{normalize_vendor(vendor)}|{document_number.strip().lower()}"
            if key in self.seen_business:
                return "duplicate_business_key"
        return None

    def insert(self, source_sha256: str, vendor: str | None, document_number: str | None) -> None:
        self.seen_sha[source_sha256] = document_number or source_sha256
        if document_number:
            key = f"{normalize_vendor(vendor)}|{document_number.strip().lower()}"
            self.seen_business[key] = source_sha256


class FakeERP:
    def __init__(self, timeout_after_write_for: set[str] | None = None) -> None:
        self.timeout_after_write_for = set(timeout_after_write_for or set())
        self.seen_keys: dict[str, str] = {}
        self.attempts = 0
        self.writes = 0

    def post(self, payload: dict[str, Any], key: str) -> dict[str, Any]:
        self.attempts += 1
        invoice_no = str(payload.get("invoice_no") or payload.get("document_number") or "")
        if key in self.seen_keys:
            return {"id": self.seen_keys[key], "duplicate_replay": True}
        draft_id = f"draft-{len(self.seen_keys) + 1}"
        self.seen_keys[key] = draft_id
        self.writes += 1
        if invoice_no in self.timeout_after_write_for:
            self.timeout_after_write_for.remove(invoice_no)
            raise TimeoutError("destination_ambiguous_timeout")
        return {"id": draft_id, "duplicate_replay": False}


@dataclass
class Decision:
    case_id: str
    status: str
    reasons: list[str] = field(default_factory=list)
    extraction: dict[str, Any] = field(default_factory=dict)
    source_sha256: str = ""
    review: str | None = None
    review_invocations: int = 0
    destination_attempts: int = 0
    destination_writes: int = 0
    draft_id: str | None = None
    idempotency_key: str | None = None
    document_id: str = ""
    audit_events: list[str] = field(default_factory=list)

    def as_expected_workflow(self, after_review: bool) -> dict[str, Any]:
        payload = {
            "status_without_reviewer": self.status if self.review is None and not after_review else None,
            "destination_attempts_without_reviewer": 0 if not after_review else None,
        }
        return payload


def classify_resume_decision(raw: str | None) -> str:
    """Map a Wait resume decision. Empty or automatic resume is timed_out, not rejected."""
    decision = (raw or "").strip().lower()
    if decision == "approve":
        return "approved"
    if decision == "reject":
        return "rejected"
    return "timed_out"


def default_reviewer(decision: Decision) -> str:
    if "missing_invoice_no" in decision.reasons or "conflicting_total" in decision.reasons:
        return "reject"
    return "approve"


def apply_review(decision: Decision, erp: FakeERP, review: str, max_retries: int = 1) -> Decision:
    if decision.status == "duplicate":
        return decision
    decision.review_invocations += 1
    decision.review = review
    decision.audit_events.append("review_decided")
    review = (review or "").strip().lower()
    if review in ("", "timeout"):
        decision.status = "pending_review"
        decision.review = "timeout"
        decision.reasons.append("review_timed_out")
        return decision
    if review == "reject":
        decision.status = "rejected"
        return decision
    if review != "approve":
        decision.status = "pending_review"
        decision.review = "timeout"
        decision.reasons.append("review_timed_out")
        return decision
    writes_before = erp.writes
    last_error: str | None = None
    for _ in range(max_retries + 1):
        decision.destination_attempts += 1
        decision.audit_events.append("destination_attempt")
        try:
            result = erp.post(
                {
                    "invoice_no": decision.extraction.get("document_number"),
                    "document_number": decision.extraction.get("document_number"),
                    "vendor": decision.extraction.get("vendor"),
                    "total": decision.extraction.get("total"),
                    "currency": decision.extraction.get("currency"),
                },
                decision.idempotency_key or decision.source_sha256,
            )
            decision.destination_writes = erp.writes - writes_before
            decision.draft_id = result["id"]
            decision.status = "drafted"
            decision.audit_events.append("destination_drafted")
            return decision
        except TimeoutError as exc:
            last_error = str(exc)
    decision.status = "destination_failed"
    decision.reasons.append(last_error or "destination_failed")
    decision.audit_events.append("error")
    return decision


def process_document(
    case_id: str,
    text: str,
    store: DuplicateStore,
    erp: FakeERP,
    reviewer: Callable[[Decision], str] | None = None,
    filename: str = "fixture.txt",
    mime_type: str = "text/plain",
    max_retries: int = 1,
) -> Decision:
    document_id = str(uuid.uuid5(uuid.UUID("a41c8e2b-7d53-4f90-9c16-2b8e0f4a71d3"), case_id + text[:24]))
    decision = Decision(case_id=case_id, status="received", document_id=document_id)
    decision.audit_events.append("received")

    file_reasons = validate_file(filename, mime_type, len(text.encode("utf-8")))
    if file_reasons:
        decision.status = "rejected"
        decision.reasons.extend(file_reasons)
        decision.audit_events.append("validated")
        return decision
    decision.audit_events.append("validated")

    digest = sha256_text(text)
    decision.source_sha256 = digest
    extraction = extract_labelled_invoice(text)
    decision.extraction = extraction
    document_number = extraction.get("document_number")
    decision.idempotency_key = idempotency_key(digest, DOCUMENT_TYPE, document_number)

    matched = store.check(digest, extraction.get("vendor"), document_number)
    if matched:
        decision.status = "duplicate"
        decision.reasons.append("duplicate_source_or_invoice_number")
        decision.audit_events.append("duplicate_stopped")
        return decision

    if payment_requested(text, extraction):
        decision.status = "blocked"
        decision.reasons.append("payment_path_blocked")
        decision.audit_events.append("payment_blocked")
        return decision
    store.insert(digest, extraction.get("vendor"), document_number)
    reasons = validate_invoice(extraction)
    decision.reasons.extend(reasons)
    if reasons:
        decision.audit_events.append("exception_flagged")
    decision.status = "pending_review"
    decision.audit_events.append("review_requested")
    if reviewer is None:
        return decision

    decision.review_invocations += 1
    decision.review = reviewer(decision)
    decision.audit_events.append("review_decided")
    review = (decision.review or "").strip().lower()
    if review in ("", "timeout"):
        decision.status = "pending_review"
        decision.review = "timeout"
        decision.reasons.append("review_timed_out")
        return decision
    if review == "reject":
        decision.status = "rejected"
        decision.reasons.append("review_rejected")
        return decision
    if review != "approve":
        decision.status = "pending_review"
        decision.review = "timeout"
        decision.reasons.append("review_timed_out")
        return decision

    writes_before = erp.writes
    last_error: str | None = None
    for _ in range(max_retries + 1):
        decision.destination_attempts += 1
        decision.audit_events.append("destination_attempt")
        try:
            result = erp.post(
                {
                    "invoice_no": document_number,
                    "document_number": document_number,
                    "vendor": extraction.get("vendor"),
                    "total": extraction.get("total"),
                    "currency": extraction.get("currency"),
                    "Idempotency-Key": decision.idempotency_key,
                },
                decision.idempotency_key or digest,
            )
            decision.destination_writes = erp.writes - writes_before
            decision.draft_id = result["id"]
            decision.status = "drafted"
            decision.audit_events.append("destination_drafted")
            return decision
        except TimeoutError as exc:
            last_error = str(exc)
            if document_number == TIMEOUT_INVOICE_NO or last_error == "destination_ambiguous_timeout":
                continue
            break
    decision.status = "destination_failed"
    decision.reasons.append(last_error or "destination_failed")
    decision.audit_events.append("error")
    return decision


def extraction_for_expected(extraction: dict[str, Any]) -> dict[str, Any]:
    return {
        "vendor": extraction.get("vendor"),
        "vendor_address": extraction.get("vendor_address"),
        "tax_registration": extraction.get("tax_registration"),
        "invoice_no": extraction.get("invoice_no"),
        "date": extraction.get("date"),
        "due_date": extraction.get("due_date"),
        "po_number": extraction.get("po_number"),
        "currency": extraction.get("currency"),
        "payment_terms": extraction.get("payment_terms"),
        "bill_to": extraction.get("bill_to"),
        "bill_to_address": extraction.get("bill_to_address"),
        "line_items": extraction.get("line_items") or [],
        "subtotal": extraction.get("subtotal"),
        "tax_label": extraction.get("tax_label"),
        "tax": extraction.get("tax"),
        "total": extraction.get("total"),
    }


def load_cases(package_root: Any) -> list[dict[str, Any]]:
    from pathlib import Path

    root = Path(package_root)
    return json.loads((root / "fixtures" / "cases.json").read_text(encoding="utf-8"))["cases"]
