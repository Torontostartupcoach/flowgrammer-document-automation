# GitHub Pages

The static landing page is published from the `docs/` folder on `main`:

https://torontostartupcoach.github.io/flowgrammer-document-automation/

GitHub Pages branch publishing is separate from the n8n validation workflow.
The validation workflow tests the Python harness and imports both workflow JSON
files into n8n 2.37.11. It does not execute the graph or the live Wait resume
path.
