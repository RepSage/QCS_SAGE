# QCS (Quality Control System — SAGE) — Codex entry point

## Canonical project instructions

`CLAUDE.md` in this repository is the single source of truth for the project's
durable instructions. Before taking any action in this project, read it
completely and apply every rule in it. Then read the current entry in
`STATUS.md`; verify dated or volatile claims against the repository and the
relevant primary artifact before relying on them.

Do not duplicate the project's architecture, qualification, corpus, release,
or verification rules here. Keeping them only in `CLAUDE.md` prevents Claude
and Codex from acquiring two subtly different versions of safety-critical
rules such as the timebase, DCPS flag semantics, worker-thread UI boundary, and
corpus-writing procedure.

## Codex mappings

- The project-file lane named `CLAUDE.md` remains canonical for both Claude and
  Codex. Durable project rules are edited there; volatile state belongs in
  `STATUS.md`; archived-data operations belong in
  `sourceCode/batch/CORPUS_LOG.md`.
- The three project agents named in `CLAUDE.md` are read-only job
  specifications under `.claude/agents/`. If delegation is explicitly
  authorized by the user or higher-level instructions, use a Codex
  collaboration agent with the corresponding specification and invariants.
  Otherwise perform the work in the main session.
- Claude-specific tool or interface names map to the closest Codex capability
  without weakening any verification, safety, release, or reporting rule.

If this file and `CLAUDE.md` ever appear to disagree, stop, re-read both from
disk, report the discrepancy, and treat `CLAUDE.md` as authoritative until the
two are reconciled.
