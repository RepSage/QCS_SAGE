# STATUS — QCS (Quality Control System — SAGE)

Volatile state, newest first. Every entry dated. Durable rules live in
`CLAUDE.md`, released program changes in `changelog/`, and everything done to
the archived DATA in `sourceCode/batch/CORPUS_LOG.md`.

The release history is NOT kept here: when a version is published its entries
leave this file, and only what is still open moves down to the open items,
dated with when it was last touched. The full text before the 2026-08-18
pruning is in git (`git show a0994bf:STATUS.md`).

## Open items

**Program and release**

- **v13.3.0 is an unpublished local release candidate** (2026-08-28). It
  replaces the GitHub-account-dependent Bugs & Suggestions shortcut with an
  internal report form that submits through a Cloudflare Worker and can copy
  the complete report as an offline fallback. The Worker has local validation,
  a honeypot, a 16 KiB body limit, a three-attempts-per-minute IP rate limit and
  nine passing tests; Wrangler 4.127.1 recognizes the binding in a deploy dry
  run. The QCS client posts in a background thread and the full self-test passes
  72/72. The Cloudflare account email was verified on 2026-08-28, the
  fine-grained `QCS feedback Worker` token was installed as the encrypted
  `GITHUB_TOKEN` Worker secret, and Worker version
  `4e637a0d-daa2-421a-b23c-20983d8f2d54` was deployed at
  `qcs-sage-feedback.qcs-sage.workers.dev`. The token has one-year expiry,
  access only to `RepSage/QCS_SAGE`, Issues read/write and the required
  Metadata read-only permission. The QCS endpoint is now wired to `/feedback`;
  `/health` returned HTTP 200 and a validation-only live POST returned the
  expected HTTP 400 without contacting GitHub. The exact released client path
  then created public Issue #41 through the Worker; the Issue page returned
  HTTP 200 with the expected title. The temporary Wrangler OAuth session was
  removed immediately afterward and `wrangler whoami` confirms that this
  machine is no longer authenticated. Off-screen Qt and Tk probes passed the
  menu order, fields, counter/copy fallback, busy state and mocked success
  flow without touching user preferences. A clean PyInstaller 6.22.2 build
  produced a 301,453,854-byte bundle containing 2,334 files; the frozen QCS
  stayed alive and responsive for its 12-second launch smoke, with no bundled
  preferences or crash log. Inno Setup 6.7.3 replaced the obsolete candidate
  with `QCS_Setup_v13.3.0.exe` (81,759,404 bytes; SHA-256
  `23F984626A21F5589454E542C1539D7E065236370B84D360801B1E9E10DF56A7`).
  The candidate is ready for owner validation but remains unpublished.
- **Pre-v13 Doppler and PAR products still need explicit requalification before
  direct comparison** (deferred 2026-08-20). The current archive contains 53
  DCPS products with four-character flags and 112 Seaguard products containing
  PAR but no `Flag_PAR`; `BURACA_FUNDA_2021S2` is the only current product with
  PAR and `Flag_PAR`. The v13.0 validation was read-only and the publication did
  not rewrite the older products.
- **v12.3 shipped four paths that were never run in the app** (2026-08-19).
  None of them blocks anything; each is one run away from being closed:
  the manual point cut and the replicate review through the worker thread
  (the point-cut MACHINERY was exercised on 2026-08-19 by the DCPS review -
  same `manual_cut_panel` and same `_show_and_wait` hop - so what is left
  unrun there is the scalar Check-variables path itself); a
  BATCH canceled in the middle (the finished files must keep their outputs
  while the interrupted one is removed - the per-file commit implements it and
  it was never executed); 'Go to visualization' landing on step 2, single file
  and batch; and a Seaguard panel under the new fixed-scale rule, which changed
  for every family while only HOBO and Doppler were looked at.
- **The FROZEN exe has never run a real qualification end to end** (open since
  v12.0; every build is launch-smoked and closes cleanly): Depth review,
  adaptive light review, replicate review, the viz tab. A launch smoke test
  cannot prove lazy imports.
- **The older-generation `.hobo` layout is not deciphered** (2026-08-14): ~30
  pre-2023 export pairs decode with a one-row offset or a partial mismatch, and
  most are refused by the reader's gates. The corpus is unaffected - it was
  qualified from the exports.

**Data** - the authoritative list is "Still open on the data" in
`sourceCode/batch/CORPUS_LOG.md`; do not duplicate it here. The root-level
`qualified_index.csv` was rebuilt on 2026-08-25 and matches direct discovery.
The former missing-manifest count is no longer actionable:
the owner deleted both raw manifests on 2026-08-13, and the special collections
that made up almost all of that count left the active corpus on 2026-08-25.

## Environment

- **There is no `gh` CLI on this machine** (2026-08-18): pull requests and
  releases go through the browser, or through the API with the token in the Git
  credential manager. Note that the automation classifier BLOCKS `git push
  --force` and the PR-merge API call; a merge is done with a local
  `git merge --no-ff` + push, and a force-push needs the owner's word first.
- **The build stack is kept**: `%TEMP%\qcs_build_env` (PyInstaller + the pinned
  runtime) and `packaging/v12_env` (PySide6 6.8.3, what `QCS.bat` launches).
  `packaging/dist/` is a build artifact; it rebuilds in about three minutes
  from `packaging/README.md`.
