# Contributing

Keep this repository lean. The current public-facing pack is `n8n/`.

## Tests

Run every Python test under `n8n/tests` with no extra packages:

```text
export PYTHONDONTWRITEBYTECODE=1
python3 n8n/tests/validate_workflows.py
python3 n8n/tests/test_wait_resume_contract.py
python3 n8n/tests/test_wait_timeout_path.py
python3 n8n/tests/test_manual_fixture_input.py
python3 n8n/tests/run_offline_harness.py
python3 n8n/tests/test_idempotency.py
```

Do not add `n8n/tests/build_workflows.py` or
`n8n/tests/build_release_archive.py` to CI. Do not install n8n, Node, or
Docker on a contributor laptop to prove import. Import smoke belongs on the
GitHub-hosted runner. A green import proves n8n 2.37.11 accepted the JSON.
It does not prove the live Wait resume item shape.

## What not to add

- Community template JSON, including template 17806
- Live credentials, customer files, or resume URLs
- Generated caches (`__pycache__`, `.pyc`, `node_modules`, `.n8n`)
- Invented live GitHub or Pages URLs
- Placeholder invoice, Power Automate, or QuickBooks assets

Report security issues through the process in SECURITY.md, not in a public
pull request.
