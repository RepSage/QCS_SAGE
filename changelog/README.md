# changelog

One file per released version, `vX.Y[.Z].md`, describing what changed in it.

## What belongs here

Changes to the **program**. A version exists when `sourceCode/*.py` outside
`batch/` changes, and `QCS_VERSION` in `QCS_DataHandler.py` moves with it.
Work on the DATA — requalifying the archive, repairing raw exports, discarding a
logger — is not a release and is recorded in
[`sourceCode/batch/CORPUS_LOG.md`](../sourceCode/batch/CORPUS_LOG.md) instead.

## Numbering

Semantic versioning, with one project-specific rule that overrides intuition:
**any change that alters qualification results — flags, thresholds, test logic —
is a MAJOR bump**, however small the diff. A file qualified under an earlier
major cannot be compared with one qualified under a later one without
requalifying, and that is exactly what a major number is for.

## Coverage

Every version from v2.2 on has a file here. The four earlier releases do not:

| version | why there is no file |
|---|---|
| v1.0 | released June 2024, before this folder existed |
| v2.0 | never recorded; reconstructed from evidence in the release notes on GitHub |
| v2.1 | `v2.1.md` exists, but it was added to the repository later, with the v2.2.1 work |
| v4.1 | never released — the work was renamed v5.0 mid-flight when it turned out to change QC output |

All 21 versions are tagged and published as GitHub Releases, so the release
notes there are complete even where this folder is not.
