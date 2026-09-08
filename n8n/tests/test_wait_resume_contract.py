#!/usr/bin/env python3
"""Regression checks for Wait parameter shape and the pre-Wait resume URL handoff.

These checks read prepared workflow JSON. They do not import n8n and they do
not assert the live Wait webhook item shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

from validate_workflows import (
    HANDOFF_NAME,
    MAIN,
    WAIT_NAME,
    load,
    outgoing,
    validate_handoff,
    validate_review_merge,
    validate_wait_parameters,
)

UNPROVEN = "UNPROVEN: live Wait resume item shape (query/body/binary) cannot be established without a live n8n execution"


def main() -> int:
    workflow = load(MAIN)
    graph = outgoing(workflow)
    errors = []
    errors.extend(validate_wait_parameters(workflow))
    errors.extend(validate_handoff(workflow, graph))
    errors.extend(validate_review_merge(workflow))
    wait = next(node for node in workflow["nodes"] if node["name"] == WAIT_NAME)
    options = (wait.get("parameters") or {}).get("options") or {}
    if "limitWaitTime" in options:
        errors.append("regression: limitWaitTime inside options must fail")
    if (wait.get("parameters") or {}).get("httpMethod") != "POST":
        errors.append("regression: Wait httpMethod must be explicit POST")
    if WAIT_NAME == "Request Human Approval":
        errors.append("regression: Wait must not use the Request Human Approval name")
    handoff_present = HANDOFF_NAME in {node["name"] for node in workflow["nodes"]}
    if not handoff_present:
        errors.append("regression: missing Prepare Reviewer Handoff")
    if errors:
        print("FAIL: wait resume contract")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: Wait v1.1 top-level timeout, pre-Wait resume_url handoff, review merge contract")
    print(UNPROVEN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
