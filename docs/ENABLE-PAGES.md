# Enable GitHub Pages later

`docs/` is ready. Pages is not enabled. Do not treat a `github.io` URL as
live.

No Pages workflow is committed. The official GitHub Actions Pages template
runs on every push to the default branch. That cannot stay unrun, and it
would fail until Pages is turned on.

## Codex enablement

1. Push `main` (separate step from this local commit).
2. Confirm `.github/workflows/validate-n8n.yml` is green.
3. In the GitHub repository: Settings → Pages → Build and deployment →
   Source → GitHub Actions.
4. Add `.github/workflows/pages.yml` using the official static Pages
   template from `actions/starter-workflows` (`pages/static.yml`), with
   `path: docs` so only this landing page is published.
5. Dispatch or push that workflow after Pages is enabled.
6. Then, and only then, put the Pages URL on the Flowgrammer article.

Official action pins from the current starter template:

- `actions/checkout@v4`
- `actions/configure-pages@v5`
- `actions/upload-pages-artifact@v3`
- `actions/deploy-pages@v5`

Required permissions: `contents: read`, `pages: write`, `id-token: write`.
Use the `github-pages` environment.

Do not upload the whole repository. The n8n JSON is not the site.

Branch-folder publishing (`main` / `docs`) is also official. Use it only if
Actions cannot be enabled. Either method stays off until a maintainer
turns Pages on.
