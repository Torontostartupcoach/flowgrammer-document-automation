# Enable GitHub Pages

`docs/` is the site source. Validate CI does not publish Pages.

No Pages workflow is committed. The official GitHub Actions Pages template
runs on every push to the default branch, so it cannot stay idle in this
tree.

## Maintainer enablement

1. Push `main`.
2. Confirm `.github/workflows/validate-n8n.yml` is green. Green import
   proves n8n 2.37.11 accepted the JSON. It does not prove the live Wait
   resume item shape.
3. In the GitHub repository: Settings → Pages → Build and deployment →
   Source → GitHub Actions.
4. Add `.github/workflows/pages.yml` using the official static Pages
   template from `actions/starter-workflows` (`pages/static.yml`), with
   `path: docs` so only this landing page is published.
5. Dispatch or push that workflow after Pages is turned on.
6. Then put the Pages URL on the Flowgrammer article.

Official action pins from the current starter template:

- `actions/checkout@v4`
- `actions/configure-pages@v5`
- `actions/upload-pages-artifact@v3`
- `actions/deploy-pages@v5`

Required permissions: `contents: read`, `pages: write`, `id-token: write`.
Use the `github-pages` environment.

Do not upload the whole repository. The n8n JSON is not the site.

Branch-folder publishing (`main` / `docs`) is also official. Use it only if
Actions cannot be used.
