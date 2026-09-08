#!/usr/bin/env python3
"""Regression: Manual Trigger must supply labelled-text JSON through Edit Fields."""

from __future__ import annotations

import sys

from validate_workflows import MAIN, load, outgoing, validate_manual_fixture


def main() -> int:
    workflow = load(MAIN)
    errors = validate_manual_fixture(workflow, outgoing(workflow))
    if workflow.get("pinData") not in ({}, None):
        errors.append("pinData must be empty")
    if errors:
        print("FAIL: manual fixture input")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: Manual Trigger → Manual Fixture Input supplies accepted labelled-text JSON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
