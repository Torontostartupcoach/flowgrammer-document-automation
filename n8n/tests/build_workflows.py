#!/usr/bin/env python3
"""Emit original Flowgrammer n8n workflow JSON. No community template copy."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

NS = uuid.UUID("a41c8e2b-7d53-4f90-9c16-2b8e0f4a71d3")
ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "workflows"


def nid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def node(
    name: str,
    ntype: str,
    type_version: int | float,
    position: list[int],
    parameters: dict,
    extra: dict | None = None,
) -> dict:
    payload = {
        "parameters": parameters,
        "id": nid(f"node:{name}"),
        "name": name,
        "type": ntype,
        "typeVersion": type_version,
        "position": position,
    }
    if extra:
        payload.update(extra)
    return payload


def conn(source: str, target: str, source_index: int = 0) -> tuple[str, int, dict]:
    return source, source_index, {"node": target, "type": "main", "index": 0}


def build_connections(edges: list[tuple[str, int, dict]]) -> dict:
    connections: dict[str, dict] = {}
    for source, index, target in edges:
        bucket = connections.setdefault(source, {"main": []})
        mains = bucket["main"]
        while len(mains) <= index:
            mains.append([])
        mains[index].append(target)
    return connections


NORMALIZE_JS = r"""const item = $input.first();
const json = item.json || {};
const binary = item.binary || {};
const hasBinary = Object.keys(binary).length > 0;
const rawText = typeof json.raw_text === 'string' ? json.raw_text : (typeof json.text === 'string' ? json.text : '');
const sourceSystem = typeof json.source_system === 'string' && json.source_system ? json.source_system : 'labelled_text_json';
return [{
  json: {
    document_id: json.document_id || $execution.id,
    document_type: json.document_type || 'invoice',
    source_system: sourceSystem,
    filename: json.filename || 'fixture.txt',
    mime_type: json.mime_type || 'text/plain',
    raw_text: rawText,
    labelled_text_ready: rawText.length > 0,
    binary_present: hasBinary,
    intake_note: (hasBinary && !rawText) ? 'Default labelled-text adapter does not read binary or webhook raw-body files. Supply JSON raw_text.' : null,
    received_at: new Date().toISOString(),
    review: { status: 'not_required', actor: null, decided_at: null },
    destination: { status: 'not_attempted', draft_id: null, attempts: 0, writes: 0 },
    audit_event_ids: ['received']
  }
}];
"""

VALIDATE_FILE_JS = r"""const rec = $input.first().json;
const name = String(rec.filename || '');
const ext = name.includes('.') ? '.' + name.split('.').pop().toLowerCase() : '';
const size = Buffer.byteLength(String(rec.raw_text || ''), 'utf8');
const reasons = [];
if (!rec.labelled_text_ready) reasons.push('missing_raw_text');
if (rec.binary_present && !rec.labelled_text_ready) reasons.push('unsupported_type');
if (rec.mime_type !== 'text/plain') reasons.push('unsupported_type');
if (ext && ext !== '.txt') reasons.push('unsupported_type');
if (size > 10 * 1024 * 1024) reasons.push('file_too_large');
rec.byte_size = size;
rec.file_ok = reasons.length === 0;
rec.validation = { ok: reasons.length === 0, exception_codes: reasons, field_errors: [] };
rec.intake_contract = 'labelled_text_json_only';
rec.audit_event_ids = (rec.audit_event_ids || []).concat(['validated']);
return [{ json: rec }];
"""

EXTRACT_JS = r"""const rec = $input.first().json;
const text = String(rec.raw_text || '');
const match = (pattern) => {
  const found = text.match(pattern);
  if (!found) return null;
  const value = found[1].trim();
  return value || null;
};
const line_items = [];
const lines = text.split(/\r?\n/);
let inItems = false;
for (const raw of lines) {
  const line = raw.trim();
  if (line.toLowerCase().startsWith('item |')) { inItems = true; continue; }
  if (inItems) {
    if (!line || line.toLowerCase().startsWith('subtotal')) { inItems = false; continue; }
    const parts = line.split('|').map((p) => p.trim());
    if (parts.length === 4) {
      line_items.push({
        description: parts[0],
        quantity: Number(parts[1]),
        unit_price: Number(parts[2]),
        amount: Number(parts[3])
      });
    }
  }
}
const invoiceNo = match(/^Invoice number:[ \t]*(.*?)\s*$/m);
rec.extraction = {
  vendor: match(/^Vendor name:\s*(.+)$/m),
  vendor_address: match(/^Vendor address:\s*(.+)$/m),
  tax_registration: match(/^GST\/HST number:\s*(.+)$/m),
  invoice_no: invoiceNo,
  document_number: invoiceNo,
  date: match(/^Invoice date:\s*(\d{4}-\d{2}-\d{2})/m),
  due_date: match(/^Due date:\s*(\d{4}-\d{2}-\d{2})/m),
  po_number: match(/^Purchase order:\s*(\S+)/m),
  currency: match(/^Currency:\s*([A-Z]{3})/m),
  payment_terms: match(/^Payment terms:\s*(.+)$/m),
  bill_to: match(/^Bill to:\s*(.+)$/m),
  bill_to_address: match(/^Bill-to address:\s*(.+)$/m),
  line_items,
  subtotal: match(/^Subtotal:\s*([\d.]+)/m) ? Number(match(/^Subtotal:\s*([\d.]+)/m)) : null,
  tax_label: match(/^Tax label:\s*(.+)$/m),
  tax: match(/^Tax:\s*([\d.]+)/m) ? Number(match(/^Tax:\s*([\d.]+)/m)) : null,
  total: match(/^Total:\s*([\d.]+)/m) ? Number(match(/^Total:\s*([\d.]+)/m)) : null,
  raw_text: text,
  model_confidence: null,
  adapter: 'labelled_text_fixture'
};
return [{ json: rec }];
"""

MANUAL_FIXTURE_TEXT = (
    "FICTIONAL TEST INVOICE — not a real supplier document\n"
    "Vendor name: Ridgemont Industrial Supply Co\n"
    "Invoice number: INV-TP-2401\n"
    "Invoice date: 2026-09-08\n"
    "Currency: CAD\n"
    "Bill to: Cedar & Quay Fabrication Ltd\n"
    "Item | Quantity | Unit price | Amount\n"
    "Safety vests | 6 | 28.00 | 168.00\n"
    "Subtotal: 168.00\n"
    "Tax label: HST 13%\n"
    "Tax: 21.84\n"
    "Total: 189.84\n"
    "Notes: Editable Manual Trigger sample. Replace raw_text with another labelled-text fixture.\n"
)

DUPLICATE_JS = r"""const rec = $input.first().json;
const staticData = $getWorkflowStaticData('global');
// Demo only. Official n8n: static data is unavailable in manual testing and only saves when a published workflow is called by a trigger or webhook. It may be unreliable at high frequency. Not a production store.
staticData.seen_sha = staticData.seen_sha || {};
staticData.seen_business = staticData.seen_business || {};
const vendor = (rec.extraction && rec.extraction.vendor) || '';
const number = (rec.extraction && rec.extraction.document_number) || '';
const business = number ? (vendor.trim().toLowerCase().replace(/\s+/g, ' ') + '|' + number.trim().toLowerCase()) : '';
let matched = null;
if (staticData.seen_sha[rec.source_sha256]) matched = 'duplicate_source';
else if (business && staticData.seen_business[business]) matched = 'duplicate_business_key';
rec.duplicate = { is_duplicate: Boolean(matched), matched_on: matched };
if (matched) {
  rec.status = 'duplicate';
  rec.validation = rec.validation || { ok: false, exception_codes: [], field_errors: [] };
  rec.validation.exception_codes = ['duplicate_source_or_invoice_number'];
  rec.audit_event_ids = (rec.audit_event_ids || []).concat(['duplicate_stopped']);
} else {
  staticData.seen_sha[rec.source_sha256] = number || rec.source_sha256;
  if (business) staticData.seen_business[business] = rec.source_sha256;
}
return [{ json: rec }];
"""

VALIDATE_SCHEMA_JS = r"""const rec = $input.first().json;
const ex = rec.extraction || {};
const reasons = [];
if (!ex.vendor) reasons.push('missing_required_field');
if (!ex.document_number) reasons.push('missing_invoice_no');
if (!ex.date) reasons.push('missing_required_field');
if (ex.total === null || ex.total === undefined || ex.total === '') reasons.push('missing_required_field');
if (ex.subtotal != null && ex.tax != null && ex.total != null) {
  if (Math.abs(Number((Number(ex.subtotal) + Number(ex.tax)).toFixed(2)) - Number(ex.total)) > 0.011) {
    reasons.push('conflicting_total');
  }
}
rec.validation = {
  ok: reasons.length === 0,
  exception_codes: reasons,
  field_errors: reasons.slice()
};
const number = ex.document_number || 'none';
rec.idempotency_material = String(rec.source_sha256 || '') + ':' + (rec.document_type || 'invoice') + ':' + number;
rec.status = 'pending_review';
rec.review = { status: 'pending', actor: null, decided_at: null };
rec.audit_event_ids = (rec.audit_event_ids || []).concat(reasons.length ? ['exception_flagged', 'review_requested'] : ['review_requested']);
return [{ json: rec }];
"""

HANDOFF_JS = r"""const rec = $input.first().json;
rec.review_handoff = {
  channel: 'manual_operator',
  resume_url: $execution.resumeUrl,
  http_method: 'POST',
  example_query: 'decision=approve',
  example_body: { decision: 'approve' },
  allowed_decisions: ['approve', 'reject'],
  operator_action: 'Copy resume_url from this item and POST decision=approve or decision=reject through a private channel. This node does not email or Slack the URL. Wait resume ships with no authentication in this JSON. Do not treat that URL as a production approval endpoint. If the 24-hour wait limit resumes with no decision, the record stays pending_review and is not rejected.'
};
rec.audit_event_ids = (rec.audit_event_ids || []).concat(['review_handoff_prepared']);
return [{ json: rec }];
"""

APPLY_REVIEW_JS = r"""const incoming = $input.first().json || {};
let rec;
try {
  rec = $('Prepare Reviewer Handoff').first().json;
} catch (error) {
  rec = incoming.document_record || incoming;
}
const query = incoming.query || {};
const body = incoming.body && typeof incoming.body === 'object' ? incoming.body : {};
const rawDecision = query.decision || body.decision || incoming.decision;
const decision = String(rawDecision == null ? '' : rawDecision).toLowerCase().trim();
let reviewStatus;
if (decision === 'approve') reviewStatus = 'approved';
else if (decision === 'reject') reviewStatus = 'rejected';
else reviewStatus = 'timed_out';
rec.review = {
  status: reviewStatus,
  actor: query.actor || body.actor || (decision === 'approve' || decision === 'reject' ? 'manual-handoff' : 'wait-limit'),
  decided_at: new Date().toISOString()
};
rec.validation = rec.validation || { ok: false, exception_codes: [], field_errors: [] };
rec.destination = rec.destination || { status: 'not_attempted', draft_id: null, attempts: 0, writes: 0 };
rec.audit_event_ids = (rec.audit_event_ids || []).concat(['review_decided']);
rec.approved = reviewStatus === 'approved';
rec.explicit_reject = reviewStatus === 'rejected';
if (reviewStatus === 'rejected') {
  rec.status = 'rejected';
  rec.validation.exception_codes = (rec.validation.exception_codes || []).concat(['review_rejected']);
} else if (reviewStatus === 'timed_out') {
  rec.status = 'pending_review';
  rec.destination.attempts = 0;
  rec.destination.status = 'not_attempted';
  rec.validation.exception_codes = (rec.validation.exception_codes || []).concat(['review_timed_out']);
}
rec.wait_resume_shape_unproven_without_live_import = true;
return [{ json: rec }];
"""

ATTEMPT_DRAFT_JS = r"""const rec = $input.first().json;
const staticData = $getWorkflowStaticData('global');
staticData.drafts = staticData.drafts || {};
const key = rec.idempotency_key;
const invoiceNo = rec.extraction && rec.extraction.document_number;
rec.destination = rec.destination || { status: 'not_attempted', draft_id: null, attempts: 0, writes: 0 };
rec.destination.attempts = (rec.destination.attempts || 0) + 1;
rec.destination.idempotency_key = key;
rec.audit_event_ids = (rec.audit_event_ids || []).concat(['destination_attempt']);
if (staticData.drafts[key]) {
  rec.destination.draft_id = staticData.drafts[key];
  rec.destination.status = 'drafted';
  rec.status = 'drafted';
  rec.ambiguous_timeout = false;
  rec.audit_event_ids.push('destination_drafted');
  return [{ json: rec }];
}
const draftId = 'draft-' + (Object.keys(staticData.drafts).length + 1);
staticData.drafts[key] = draftId;
rec.destination.writes = (rec.destination.writes || 0) + 1;
rec.destination.draft_id = draftId;
if (invoiceNo === 'INV-TP-2405') {
  rec.ambiguous_timeout = true;
  rec.destination.status = 'failed_ambiguous';
  rec.status = 'pending_review';
  rec.audit_event_ids.push('destination_ambiguous_timeout');
  return [{ json: rec }];
}
rec.ambiguous_timeout = false;
rec.destination.status = 'drafted';
rec.status = 'drafted';
rec.audit_event_ids.push('destination_drafted');
return [{ json: rec }];
"""

RETRY_DRAFT_JS = r"""const rec = $input.first().json;
const staticData = $getWorkflowStaticData('global');
staticData.drafts = staticData.drafts || {};
const key = rec.idempotency_key;
rec.destination = rec.destination || { status: 'not_attempted', draft_id: null, attempts: 0, writes: 0 };
rec.destination.attempts = (rec.destination.attempts || 0) + 1;
rec.destination.idempotency_key = key;
rec.audit_event_ids = (rec.audit_event_ids || []).concat(['destination_attempt']);
if (!staticData.drafts[key]) {
  rec.destination.status = 'failed';
  rec.status = 'destination_failed';
  rec.ambiguous_timeout = false;
  return [{ json: rec }];
}
rec.destination.draft_id = staticData.drafts[key];
rec.destination.status = 'drafted';
rec.status = 'drafted';
rec.ambiguous_timeout = false;
rec.audit_event_ids.push('destination_drafted');
return [{ json: rec }];
"""

AUDIT_JS = r"""const rec = $input.first().json;
rec.audit_event_ids = rec.audit_event_ids || [];
if (!rec.audit_event_ids.includes('result')) rec.audit_event_ids.push('result');
rec.result = {
  document_id: rec.document_id,
  status: rec.status,
  reasons: (rec.validation && rec.validation.exception_codes) || [],
  review: rec.review,
  destination: rec.destination,
  idempotency_key: rec.idempotency_key,
  source_sha256: rec.source_sha256
};
return [{ json: rec }];
"""

STOP_DUP_JS = r"""const rec = $input.first().json;
rec.status = 'duplicate';
rec.review = { status: 'not_required', actor: null, decided_at: null };
rec.destination = { status: 'skipped', draft_id: null, attempts: 0, writes: 0 };
return [{ json: rec }];
"""

REJECT_FILE_JS = r"""const rec = $input.first().json;
rec.status = 'rejected';
rec.error_message = (rec.validation.exception_codes || []).join(',');
return [{ json: rec }];
"""

ERROR_AUDIT_JS = r"""const item = $input.first().json;
const execution = item.execution || {};
return [{
  json: {
    event: 'error',
    workflow_name: (item.workflow || {}).name || 'unknown',
    execution_id: execution.id || null,
    destination: { status: 'not_attempted', draft_id: null, attempts: 0, writes: 0 },
    note: 'Error workflow writes no draft. Replace this Set with a Credentials-backed alert after import.'
  }
}];
"""


def crypto_hash(name: str, position: list[int], value: str, property_name: str) -> dict:
    """Official Crypto node. Hash action needs no credentials and no NODE_FUNCTION_ALLOW_BUILTIN."""
    return node(
        name,
        "n8n-nodes-base.crypto",
        1,
        position,
        {
            "action": "hash",
            "binaryData": False,
            "type": "SHA256",
            "value": value,
            "dataPropertyName": property_name,
            "encoding": "hex",
        },
    )


def main_workflow() -> dict:
    nodes = [
        node("Manual Trigger", "n8n-nodes-base.manualTrigger", 1, [80, 240], {}),
        node(
            "Manual Fixture Input",
            "n8n-nodes-base.set",
            3.4,
            [220, 240],
            {
                "assignments": {
                    "assignments": [
                        {
                            "id": nid("set:raw-text"),
                            "name": "raw_text",
                            "value": MANUAL_FIXTURE_TEXT,
                            "type": "string",
                        },
                        {
                            "id": nid("set:filename"),
                            "name": "filename",
                            "value": "manual-fixture.txt",
                            "type": "string",
                        },
                        {
                            "id": nid("set:mime"),
                            "name": "mime_type",
                            "value": "text/plain",
                            "type": "string",
                        },
                        {
                            "id": nid("set:source"),
                            "name": "source_system",
                            "value": "labelled_text_json",
                            "type": "string",
                        },
                    ]
                },
                "includeOtherFields": False,
            },
        ),
        node(
            "Webhook Intake",
            "n8n-nodes-base.webhook",
            2,
            [80, 420],
            {
                "httpMethod": "POST",
                "path": "fg-document-intake",
                "options": {},
            },
            extra={"webhookId": nid("webhook:fg-document-intake")},
        ),
        node("Normalize Intake", "n8n-nodes-base.code", 2, [360, 320], {"jsCode": NORMALIZE_JS}),
        node("Validate MIME and Size", "n8n-nodes-base.code", 2, [600, 320], {"jsCode": VALIDATE_FILE_JS}),
        node(
            "File Valid?",
            "n8n-nodes-base.if",
            2,
            [840, 320],
            {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [
                        {
                            "id": nid("if:file-valid"),
                            "leftValue": "={{ $json.file_ok }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true"},
                        }
                    ],
                    "combinator": "and",
                }
            },
        ),
        node("Reject Unsupported File", "n8n-nodes-base.code", 2, [1080, 520], {"jsCode": REJECT_FILE_JS}),
        node(
            "Stop Unsupported File",
            "n8n-nodes-base.stopAndError",
            1,
            [1320, 520],
            {"errorType": "errorMessage", "errorMessage": "={{ $json.error_message }}"},
        ),
        crypto_hash(
            "Hash Source SHA-256",
            [1080, 240],
            "={{ $json.raw_text || '' }}",
            "source_sha256",
        ),
        node("Extract Labelled Text", "n8n-nodes-base.code", 2, [1320, 240], {"jsCode": EXTRACT_JS}),
        node("Check Duplicates", "n8n-nodes-base.code", 2, [1560, 240], {"jsCode": DUPLICATE_JS}),
        node(
            "Duplicate?",
            "n8n-nodes-base.if",
            2,
            [1800, 240],
            {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [
                        {
                            "id": nid("if:duplicate"),
                            "leftValue": "={{ $json.duplicate.is_duplicate }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true"},
                        }
                    ],
                    "combinator": "and",
                }
            },
        ),
        node("Stop Duplicate", "n8n-nodes-base.code", 2, [2040, 80], {"jsCode": STOP_DUP_JS}),
        node("Validate Schema and Totals", "n8n-nodes-base.code", 2, [2040, 320], {"jsCode": VALIDATE_SCHEMA_JS}),
        crypto_hash(
            "Hash Idempotency Key",
            [2280, 320],
            "={{ $json.idempotency_material }}",
            "idempotency_key",
        ),
        node("Prepare Reviewer Handoff", "n8n-nodes-base.code", 2, [2520, 320], {"jsCode": HANDOFF_JS}),
        node(
            "Wait For Manual Reviewer Handoff",
            "n8n-nodes-base.wait",
            1.1,
            [2760, 320],
            {
                "resume": "webhook",
                "httpMethod": "POST",
                "limitWaitTime": True,
                "limitType": "afterTimeInterval",
                "resumeAmount": 24,
                "resumeUnit": "hours",
            },
            extra={"webhookId": nid("wait:review")},
        ),
        node("Apply Review Decision", "n8n-nodes-base.code", 2, [3000, 320], {"jsCode": APPLY_REVIEW_JS}),
        node(
            "Approved?",
            "n8n-nodes-base.if",
            2,
            [3240, 320],
            {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [
                        {
                            "id": nid("if:approved"),
                            "leftValue": "={{ $json.approved }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true"},
                        }
                    ],
                    "combinator": "and",
                }
            },
        ),
        node(
            "Explicit Reject?",
            "n8n-nodes-base.if",
            2,
            [3480, 400],
            {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [
                        {
                            "id": nid("if:explicit-reject"),
                            "leftValue": "={{ $json.explicit_reject }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true"},
                        }
                    ],
                    "combinator": "and",
                }
            },
        ),
        node("Record Review Timeout", "n8n-nodes-base.code", 2, [3720, 520], {"jsCode": AUDIT_JS}),
        node("Attempt Draft Write", "n8n-nodes-base.code", 2, [3480, 200], {"jsCode": ATTEMPT_DRAFT_JS}),
        node(
            "Ambiguous Timeout?",
            "n8n-nodes-base.if",
            2,
            [3720, 200],
            {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [
                        {
                            "id": nid("if:ambiguous-timeout"),
                            "leftValue": "={{ $json.ambiguous_timeout }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true"},
                        }
                    ],
                    "combinator": "and",
                }
            },
        ),
        node("Retry Draft Write", "n8n-nodes-base.code", 2, [3960, 80], {"jsCode": RETRY_DRAFT_JS}),
        node(
            "Optional Draft HTTP",
            "n8n-nodes-base.httpRequest",
            4.2,
            [3480, 520],
            {
                "method": "POST",
                "url": "https://example.invalid/fake-erp/drafts",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "Idempotency-Key",
                            "value": "={{ $json.idempotency_key }}",
                        }
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ $json.result || $json }}",
                "options": {},
            },
            extra={"disabled": True},
        ),
        node("Record Rejection", "n8n-nodes-base.code", 2, [3720, 400], {"jsCode": AUDIT_JS}),
        node("Append Audit Result", "n8n-nodes-base.code", 2, [4200, 240], {"jsCode": AUDIT_JS}),
    ]
    edges = [
        conn("Manual Trigger", "Manual Fixture Input"),
        conn("Manual Fixture Input", "Normalize Intake"),
        conn("Webhook Intake", "Normalize Intake"),
        conn("Normalize Intake", "Validate MIME and Size"),
        conn("Validate MIME and Size", "File Valid?"),
        conn("File Valid?", "Hash Source SHA-256", 0),
        conn("File Valid?", "Reject Unsupported File", 1),
        conn("Reject Unsupported File", "Stop Unsupported File"),
        conn("Hash Source SHA-256", "Extract Labelled Text"),
        conn("Extract Labelled Text", "Check Duplicates"),
        conn("Check Duplicates", "Duplicate?"),
        conn("Duplicate?", "Stop Duplicate", 0),
        conn("Duplicate?", "Validate Schema and Totals", 1),
        conn("Stop Duplicate", "Append Audit Result"),
        conn("Validate Schema and Totals", "Hash Idempotency Key"),
        conn("Hash Idempotency Key", "Prepare Reviewer Handoff"),
        conn("Prepare Reviewer Handoff", "Wait For Manual Reviewer Handoff"),
        conn("Wait For Manual Reviewer Handoff", "Apply Review Decision"),
        conn("Apply Review Decision", "Approved?"),
        conn("Approved?", "Attempt Draft Write", 0),
        conn("Approved?", "Explicit Reject?", 1),
        conn("Explicit Reject?", "Record Rejection", 0),
        conn("Explicit Reject?", "Record Review Timeout", 1),
        conn("Record Review Timeout", "Append Audit Result"),
        conn("Attempt Draft Write", "Ambiguous Timeout?"),
        conn("Ambiguous Timeout?", "Retry Draft Write", 0),
        conn("Ambiguous Timeout?", "Append Audit Result", 1),
        conn("Retry Draft Write", "Append Audit Result"),
        conn("Record Rejection", "Append Audit Result"),
    ]
    return {
        "name": "Flowgrammer Document Processing Starter",
        "id": nid("workflow:main"),
        "versionId": nid("workflow:main:version"),
        "active": False,
        "isArchived": False,
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": False},
        "tags": [],
        "settings": {
            "executionOrder": "v1",
            "callerPolicy": "workflowsFromSameOwner",
        },
        "nodes": nodes,
        "connections": build_connections(edges),
    }


def error_workflow() -> dict:
    nodes = [
        node("Error Trigger", "n8n-nodes-base.errorTrigger", 1, [240, 300], {}),
        node("Build Error Audit", "n8n-nodes-base.code", 2, [500, 300], {"jsCode": ERROR_AUDIT_JS}),
        node(
            "Prepare Alert Payload",
            "n8n-nodes-base.set",
            3.4,
            [760, 300],
            {
                "assignments": {
                    "assignments": [
                        {
                            "id": nid("set:alert"),
                            "name": "alert_channel",
                            "value": "REPLACE_AFTER_IMPORT",
                            "type": "string",
                        },
                        {
                            "id": nid("set:note"),
                            "name": "writes_draft",
                            "value": "no",
                            "type": "string",
                        },
                    ]
                },
                "includeOtherFields": True,
            },
        ),
    ]
    edges = [
        conn("Error Trigger", "Build Error Audit"),
        conn("Build Error Audit", "Prepare Alert Payload"),
    ]
    return {
        "name": "Flowgrammer Document Processing Error Workflow",
        "id": nid("workflow:error"),
        "versionId": nid("workflow:error:version"),
        "active": False,
        "isArchived": False,
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": False},
        "tags": [],
        "settings": {"executionOrder": "v1"},
        "nodes": nodes,
        "connections": build_connections(edges),
    }


def write_workflows() -> dict[str, Path]:
    WORKFLOWS.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, payload in (
        ("flowgrammer-document-processing.json", main_workflow()),
        ("flowgrammer-document-processing-error.json", error_workflow()),
    ):
        path = WORKFLOWS / name
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written[name] = path
    return written


if __name__ == "__main__":
    for name, path in write_workflows().items():
        print(f"wrote {path} ({name})")
