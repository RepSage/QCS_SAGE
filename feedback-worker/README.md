# QCS feedback Worker

Receives the QCS in-app feedback form and creates an Issue in
`RepSage/QCS_SAGE`. The GitHub credential exists only as the encrypted
`GITHUB_TOKEN` Cloudflare secret; it is never shipped with QCS or returned by
the endpoint.

## Security boundary

- Accepts only `POST /feedback` with a JSON body of at most 16 KiB.
- Revalidates the optional name, required title, required description and QCS
  version independently of the desktop application.
- Limits each source IP to three submission attempts per 60 seconds through a
  Cloudflare rate-limiting binding. The binding is deliberately a mitigation,
  not authentication: the public form accepts reports from unauthenticated QCS
  operators.
- Uses a fine-grained GitHub token restricted to this repository with only
  **Issues: Read and write**. No token belongs in `.dev.vars`, the source tree,
  test output, screenshots or release artifacts.
- Returns only the public Issue number and URL. Upstream failure bodies and the
  GitHub token never reach the caller.

## Local verification

Use the bundled Node runtime on this machine and install the pinned Wrangler:

```powershell
$nodeRoot = 'C:\Users\LAMB\.cache\codex-runtimes\codex-primary-runtime\dependencies\node'
$env:PATH = "$nodeRoot\bin;" + $env:PATH
& "$nodeRoot\bin\node.exe" "$nodeRoot\node_modules\pnpm\bin\pnpm.cjs" install --dir feedback-worker
Push-Location feedback-worker
& "$nodeRoot\bin\node.exe" --test
& ".\node_modules\.bin\wrangler.cmd" deploy --dry-run
Pop-Location
```

## First deployment

1. Create a fine-grained personal access token limited to `RepSage/QCS_SAGE`
   with **Issues: Read and write** and no other repository write permission.
2. Run `wrangler login --device` and approve the displayed device code within
   five minutes. Add `--use-keyring` when the Wrangler keyring helper is
   available. On this machine the bundled Node runtime has no `npm`, so the
   helper cannot be installed automatically; use the OAuth file only for this
   deployment session and log out immediately afterward.
3. From this directory, run `wrangler secret put GITHUB_TOKEN`. Paste the token
   only at Wrangler's secret prompt. Cloudflare creates a Worker version and
   deploys it without printing the secret.
4. Run `wrangler deploy`, then call `GET /health` and submit one controlled test
   Issue through `POST /feedback`.
5. Run `wrangler logout` and verify that the temporary local OAuth session was
   removed.

Cloudflare's `workers.dev` URL produced by the deploy is the only value added to
the QCS source. Never add the GitHub token or Cloudflare OAuth material.

Production endpoint:
`https://qcs-sage-feedback.qcs-sage.workers.dev/feedback`.
