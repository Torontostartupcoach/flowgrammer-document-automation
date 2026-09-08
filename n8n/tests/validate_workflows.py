#!/usr/bin/env python3
"""Validate n8n JSON parameter shape and graph behaviour without importing n8n."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "workflows" / "flowgrammer-document-processing.json"
ERROR = ROOT / "workflows" / "flowgrammer-document-processing-error.json"

FORBIDDEN_TYPES = {
    "n8n-nodes-base.stripe",
    "n8n-nodes-base.paypal",
    "n8n-nodes-base.quickbooks",
    "n8n-nodes-base.xero",
    "n8n-nodes-base.shopify",
    "n8n-nodes-base.wise",
}
FORBIDDEN_TEXT = (
    "17806",
    "/Users/",
    "/home/",
    "C:\\Users\\",
    "sk-proj-",
    "xoxb-",
    "BEGIN PRIVATE KEY",
    "Request Human Approval",
    "_timeout_replayed",
    "require('crypto')",
    'require("crypto")',
    "NODE_FUNCTION_ALLOW_BUILTIN",
)
REQUIRE_CRYPTO = re.compile(r"""require\s*\(\s*['"]crypto['"]\s*\)""")
REQUIRED_MAIN_NODES = {
    "Manual Trigger",
    "Manual Fixture Input",
    "Webhook Intake",
    "Normalize Intake",
    "Validate MIME and Size",
    "Hash Source SHA-256",
    "Extract Labelled Text",
    "Check Duplicates",
    "Hash Idempotency Key",
    "Prepare Reviewer Handoff",
    "Wait For Manual Reviewer Handoff",
    "Apply Review Decision",
    "Attempt Draft Write",
    "Ambiguous Timeout?",
    "Retry Draft Write",
    "Explicit Reject?",
    "Record Review Timeout",
    "Append Audit Result",
}
REQUIRED_ERROR_NODES = {"Error Trigger", "Build Error Audit"}
WAIT_NAME = "Wait For Manual Reviewer Handoff"
HANDOFF_NAME = "Prepare Reviewer Handoff"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def node_by_name(workflow: dict, name: str) -> dict:
    return next(node for node in workflow["nodes"] if node["name"] == name)


def node_names(workflow: dict) -> set[str]:
    return {node["name"] for node in workflow["nodes"]}


def outgoing(workflow: dict) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {name: [] for name in node_names(workflow)}
    for source, payload in workflow.get("connections", {}).items():
        for branch in payload.get("main", []):
            for target in branch:
                graph.setdefault(source, []).append(target["node"])
    return graph


def outgoing_branches(workflow: dict) -> dict[str, list[list[str]]]:
    branches: dict[str, list[list[str]]] = {}
    for source, payload in workflow.get("connections", {}).items():
        branches[source] = [
            [target["node"] for target in branch] for branch in payload.get("main", [])
        ]
    return branches


def reachable(graph: dict[str, list[str]], starts: list[str]) -> set[str]:
    seen: set[str] = set()
    stack = list(starts)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(graph.get(name, []))
    return seen


def code_of(workflow: dict, name: str) -> str:
    return str(node_by_name(workflow, name).get("parameters", {}).get("jsCode") or "")


def all_code(workflow: dict) -> str:
    return "\n".join(code_of(workflow, node["name"]) for node in workflow["nodes"] if node.get("type") == "n8n-nodes-base.code")


def validate_wait_parameters(workflow: dict) -> list[str]:
    errors: list[str] = []
    wait = node_by_name(workflow, WAIT_NAME)
    params = wait.get("parameters") or {}
    options = params.get("options") or {}
    if wait.get("type") != "n8n-nodes-base.wait":
        errors.append("Wait node has the wrong type")
    if wait.get("typeVersion") != 1.1:
        errors.append("Wait typeVersion must be 1.1")
    if params.get("resume") != "webhook":
        errors.append("Wait resume must be webhook")
    if params.get("httpMethod") != "POST":
        errors.append("Wait httpMethod must be an explicit POST; do not assume the default")
    if "limitWaitTime" in options:
        errors.append("Wait limitWaitTime must not live inside options; n8n v1.1 ignores that")
    if params.get("limitWaitTime") is not True:
        errors.append("Wait limitWaitTime must be a top-level true boolean")
    if params.get("limitType") != "afterTimeInterval":
        errors.append("Wait limitType must be top-level afterTimeInterval")
    if params.get("resumeAmount") != 24:
        errors.append("Wait resumeAmount must be top-level 24")
    if params.get("resumeUnit") != "hours":
        errors.append("Wait resumeUnit must be top-level hours")
    if "approval" in WAIT_NAME.lower() and "request" in WAIT_NAME.lower():
        errors.append("Wait node must not claim it requests approval")
    return errors


def validate_handoff(workflow: dict, graph: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    handoff = code_of(workflow, HANDOFF_NAME)
    if "$execution.resumeUrl" not in handoff:
        errors.append("Prepare Reviewer Handoff must output $execution.resumeUrl")
    if "resume_url" not in handoff:
        errors.append("Prepare Reviewer Handoff must expose resume_url on the item")
    if "Hash Idempotency Key" not in graph.get("Validate Schema and Totals", []):
        errors.append("schema validation must hash the idempotency material before handoff")
    if HANDOFF_NAME not in graph.get("Hash Idempotency Key", []):
        errors.append("handoff node must run after Hash Idempotency Key")
    if WAIT_NAME not in graph.get(HANDOFF_NAME, []):
        errors.append("Wait must follow Prepare Reviewer Handoff in the same path")
    if WAIT_NAME in graph.get("Validate Schema and Totals", []):
        errors.append("Wait must not be reached without the handoff node")
    if WAIT_NAME in graph.get("Hash Idempotency Key", []):
        errors.append("Wait must not skip Prepare Reviewer Handoff")
    return errors


def validate_review_merge(workflow: dict) -> list[str]:
    errors: list[str] = []
    apply_js = code_of(workflow, "Apply Review Decision")
    if "$('Prepare Reviewer Handoff')" not in apply_js and '$("Prepare Reviewer Handoff")' not in apply_js:
        errors.append("Apply Review Decision must read the original record from Prepare Reviewer Handoff")
    if "incoming.query" not in apply_js or "incoming.body" not in apply_js:
        errors.append("Apply Review Decision must read resume query and body")
    if "wait_resume_shape_unproven_without_live_import" not in apply_js:
        errors.append("Apply Review Decision must mark Wait resume item shape as unproven")
    if "decision === 'reject'" not in apply_js:
        errors.append("Apply Review Decision must reject only on explicit decision=reject")
    if "timed_out" not in apply_js or "review_timed_out" not in apply_js:
        errors.append("Apply Review Decision must map empty or automatic resume to timed_out")
    if "else if (!rec.approved)" in apply_js and "reviewStatus === 'rejected'" not in apply_js:
        errors.append("empty decision must not fall through to rejected")
    return errors


def validate_retry_graph(workflow: dict, graph: dict[str, list[str]], branches: dict[str, list[list[str]]]) -> list[str]:
    errors: list[str] = []
    attempt = node_by_name(workflow, "Attempt Draft Write")
    retry = node_by_name(workflow, "Retry Draft Write")
    if attempt["id"] == retry["id"]:
        errors.append("Attempt and Retry must be distinct nodes")
    if attempt.get("type") != "n8n-nodes-base.code" or retry.get("type") != "n8n-nodes-base.code":
        errors.append("destination attempts must be Code nodes")
    approve_true = (branches.get("Approved?") or [[]])[0]
    if "Attempt Draft Write" not in approve_true:
        errors.append("approve path must enter Attempt Draft Write")
    if "Retry Draft Write" in approve_true:
        errors.append("retry must not run on the first destination edge")
    approve_false = (branches.get("Approved?") or [[], []])[1] if len(branches.get("Approved?") or []) > 1 else []
    if "Record Rejection" in approve_false:
        errors.append("non-approve path must distinguish reject from automatic timeout")
    if "Explicit Reject?" not in approve_false:
        errors.append("non-approve path must enter Explicit Reject?")
    reject_branches = branches.get("Explicit Reject?") or [[]]
    reject_true = reject_branches[0]
    reject_false = reject_branches[1] if len(reject_branches) > 1 else []
    if "Record Rejection" not in reject_true:
        errors.append("explicit reject true branch must be Record Rejection")
    if "Record Review Timeout" not in reject_false:
        errors.append("automatic timeout must go to Record Review Timeout, not reject")
    if "Attempt Draft Write" in reject_true or "Attempt Draft Write" in reject_false:
        errors.append("timeout or reject must not call the destination")
    if "Ambiguous Timeout?" not in graph.get("Attempt Draft Write", []):
        errors.append("first destination attempt must branch on ambiguous timeout")
    timeout_branches = branches.get("Ambiguous Timeout?") or [[]]
    timeout_true = timeout_branches[0]
    timeout_false = timeout_branches[1] if len(timeout_branches) > 1 else []
    if "Retry Draft Write" not in timeout_true:
        errors.append("ambiguous timeout true branch must be Retry Draft Write")
    if "Append Audit Result" not in timeout_false:
        errors.append("successful first write must skip retry")
    if "Append Audit Result" not in graph.get("Retry Draft Write", []):
        errors.append("retry must reach audit")
    attempt_js = code_of(workflow, "Attempt Draft Write")
    retry_js = code_of(workflow, "Retry Draft Write")
    if attempt_js.count("destination.attempts =") != 1 or retry_js.count("destination.attempts =") != 1:
        errors.append("each destination node must increment destination.attempts exactly once")
    if "_timeout_replayed" in attempt_js or "_timeout_replayed" in retry_js:
        errors.append("simulated in-node retry counter is forbidden")
    if "idempotency_key" not in attempt_js or "idempotency_key" not in retry_js:
        errors.append("both destination nodes must use the same idempotency_key field")
    if re.search(r"writes\s*\+|writes\s*=", retry_js):
        errors.append("Retry Draft Write must not increment writes")
    if "INV-TP-2405" not in attempt_js:
        errors.append("first attempt must flag the timeout fixture")
    if "INV-TP-2405" in retry_js:
        errors.append("retry must look up the stored key, not re-simulate the timeout fixture")
    if "staticData.drafts" not in attempt_js or "staticData.drafts" not in retry_js:
        errors.append("both destination nodes must share the stored draft map")
    return errors


def validate_manual_fixture(workflow: dict, graph: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    if "Manual Fixture Input" not in graph.get("Manual Trigger", []):
        errors.append("Manual Trigger must connect to Manual Fixture Input")
    if "Normalize Intake" in graph.get("Manual Trigger", []):
        errors.append("Manual Trigger must not connect straight to Normalize Intake")
    if "Normalize Intake" not in graph.get("Manual Fixture Input", []):
        errors.append("Manual Fixture Input must connect to Normalize Intake")
    fixture = node_by_name(workflow, "Manual Fixture Input")
    if fixture.get("type") != "n8n-nodes-base.set":
        errors.append("Manual Fixture Input must be an Edit Fields (Set) node")
    if fixture.get("typeVersion") not in (3.4, 3, 3.3, 3.2):
        errors.append("Manual Fixture Input must use a current Set/Edit Fields typeVersion")
    params = fixture.get("parameters") or {}
    assignments = ((params.get("assignments") or {}).get("assignments")) or []
    values = {str(item.get("name")): str(item.get("value") or "") for item in assignments}
    if not values.get("raw_text"):
        errors.append("Manual Fixture Input must supply raw_text")
    if "Vendor name:" not in values.get("raw_text", "") or "Invoice number:" not in values.get("raw_text", ""):
        errors.append("Manual Fixture Input raw_text must be labelled-text JSON content")
    if values.get("mime_type") != "text/plain":
        errors.append("Manual Fixture Input mime_type must be text/plain")
    if not values.get("filename") or not values["filename"].endswith(".txt"):
        errors.append("Manual Fixture Input filename must be a .txt labelled-text name")
    if values.get("source_system") != "labelled_text_json":
        errors.append("Manual Fixture Input source_system must be labelled_text_json")
    if params.get("includeOtherFields") is True:
        errors.append("Manual Fixture Input must keep only the accepted JSON fields")
    if workflow.get("pinData") not in ({}, None):
        errors.append("pinData must stay empty; fixture values live in the Set node")
    return errors


def validate_normalize(workflow: dict) -> list[str]:
    errors: list[str] = []
    normalize = code_of(workflow, "Normalize Intake")
    validate = code_of(workflow, "Validate MIME and Size")
    if "$node['Manual Trigger']" in normalize or '$node["Manual Trigger"]' in normalize:
        errors.append("Normalize Intake must not depend on an unexecuted Manual Trigger node")
    if "json.raw_text" not in normalize:
        errors.append("Normalize Intake must read JSON raw_text")
    if "labelled_text_ready" not in normalize:
        errors.append("Normalize Intake must flag labelled_text_ready")
    if "does not read binary" not in normalize:
        errors.append("Normalize Intake must refuse to describe binary as labelled text")
    webhook = node_by_name(workflow, "Webhook Intake")
    if (webhook.get("parameters") or {}).get("options", {}).get("rawBody") is True:
        errors.append("default Webhook must not enable Raw body; labelled-text JSON is the accepted input")
    if "missing_raw_text" not in validate:
        errors.append("file validation must reject missing raw_text")
    if "application/pdf" in validate or "image/png" in validate or "image/jpeg" in validate:
        errors.append("default MIME allow-list must not pass PDF or image binaries")
    if "text/plain" not in validate or "labelled_text_json_only" not in validate:
        errors.append("file validation must accept only labelled-text JSON as text/plain")
    return errors


def validate_crypto_nodes(workflow: dict, graph: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    expected = (
        ("Hash Source SHA-256", "source_sha256", "raw_text", "Extract Labelled Text"),
        ("Hash Idempotency Key", "idempotency_key", "idempotency_material", HANDOFF_NAME),
    )
    for name, property_name, value_token, next_name in expected:
        node = node_by_name(workflow, name)
        params = node.get("parameters") or {}
        if node.get("type") != "n8n-nodes-base.crypto":
            errors.append(f"{name} must be n8n-nodes-base.crypto, not a Code require")
        if node.get("typeVersion") not in (1, 1.0, 2):
            errors.append(f"{name} typeVersion must be a Crypto hash version")
        if params.get("action") != "hash":
            errors.append(f"{name} action must be hash")
        if params.get("type") != "SHA256":
            errors.append(f"{name} type must be SHA256")
        if params.get("encoding") != "hex":
            errors.append(f"{name} encoding must be hex")
        if params.get("binaryData") is True:
            errors.append(f"{name} default must hash text, not binary")
        if params.get("dataPropertyName") != property_name:
            errors.append(f"{name} must write {property_name}")
        if value_token not in str(params.get("value") or ""):
            errors.append(f"{name} value expression must use {value_token}")
        if node.get("credentials"):
            errors.append(f"{name} must not attach credentials")
        if next_name not in graph.get(name, []):
            errors.append(f"{name} must connect to {next_name}")
    schema = code_of(workflow, "Validate Schema and Totals")
    if "idempotency_material" not in schema:
        errors.append("Validate Schema must build idempotency_material without hashing")
    if "createHash" in schema or "source_sha256" in schema and "digest" in schema:
        if "createHash" in schema or "digest(" in schema:
            errors.append("Validate Schema must not hash")
    if REQUIRE_CRYPTO.search(all_code(workflow)):
        errors.append("Code nodes must not require('crypto'); use the official Crypto node")
    return errors


def validate_workflow(path: Path, required: set[str], starts: list[str], error_ok: bool) -> list[str]:
    errors: list[str] = []
    workflow = load(path)
    text = path.read_text(encoding="utf-8")
    if not workflow.get("name"):
        errors.append(f"{path.name}: missing name")
    if workflow.get("active") is True:
        errors.append(f"{path.name}: workflow must ship inactive")
    if workflow.get("pinData") not in ({}, None):
        errors.append(f"{path.name}: pinData must be empty")
    names = node_names(workflow)
    missing = required - names
    if missing:
        errors.append(f"{path.name}: missing nodes {sorted(missing)}")
    ids = [node.get("id") for node in workflow["nodes"]]
    if len(ids) != len(set(ids)):
        errors.append(f"{path.name}: duplicate node ids")
    for node in workflow["nodes"]:
        ntype = node.get("type") or ""
        if ntype in FORBIDDEN_TYPES:
            errors.append(f"{path.name}: forbidden node type {ntype}")
        if node.get("credentials"):
            errors.append(f"{path.name}: {node['name']} has credentials object")
        if REQUIRE_CRYPTO.search(json.dumps(node)):
            errors.append(f"{path.name}: {node['name']} uses require('crypto')")
    graph = outgoing(workflow)
    branches = outgoing_branches(workflow)
    seen = reachable(graph, starts)
    isolated = names - seen
    if isolated and not error_ok:
        leftover = isolated - {"Optional Draft HTTP"}
        if leftover:
            errors.append(f"{path.name}: unreachable nodes {sorted(leftover)}")
    if not error_ok:
        errors.extend(validate_wait_parameters(workflow))
        errors.extend(validate_handoff(workflow, graph))
        errors.extend(validate_review_merge(workflow))
        errors.extend(validate_retry_graph(workflow, graph, branches))
        errors.extend(validate_normalize(workflow))
        errors.extend(validate_manual_fixture(workflow, graph))
        errors.extend(validate_crypto_nodes(workflow, graph))
        if "Attempt Draft Write" in graph.get("Check Duplicates", []):
            errors.append(f"{path.name}: destination reachable without review")
        if "Attempt Draft Write" in graph.get(WAIT_NAME, []):
            errors.append(f"{path.name}: destination reachable without Apply Review Decision")
    if error_ok:
        dest_types = {node["type"] for node in workflow["nodes"]}
        if "n8n-nodes-base.httpRequest" in dest_types:
            errors.append(f"{path.name}: error workflow must not call a destination HTTP node")
        if "Attempt Draft Write" in names or "Retry Draft Write" in names:
            errors.append(f"{path.name}: error workflow must not write a draft")
    for needle in FORBIDDEN_TEXT:
        if needle in text:
            errors.append(f"{path.name}: forbidden token {needle}")
    if re.search(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}", text):
        errors.append(f"{path.name}: credential-like assignment")
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(
        validate_workflow(
            MAIN,
            REQUIRED_MAIN_NODES,
            ["Manual Trigger", "Webhook Intake"],
            error_ok=False,
        )
    )
    errors.extend(
        validate_workflow(
            ERROR,
            REQUIRED_ERROR_NODES,
            ["Error Trigger"],
            error_ok=True,
        )
    )
    main_wf = load(MAIN)
    error_wf = load(ERROR)
    if main_wf["id"] == error_wf["id"]:
        errors.append("main and error workflows share an id")
    if "17806" in json.dumps(main_wf) or "17806" in json.dumps(error_wf):
        errors.append("community template identifier 17806 present")
    if errors:
        print("FAIL: workflow JSON validation")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        f"PASS: {MAIN.name} nodes={len(main_wf['nodes'])} "
        f"{ERROR.name} nodes={len(error_wf['nodes'])} workflows=2"
    )
    print("NOTE: Wait webhook resume item shape is unproven without a live n8n import.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
