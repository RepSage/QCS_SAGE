# -*- coding: utf-8 -*-
"""Promote the validated RRDM 23a candidate products into the active archive.

    promote_rrdm_23a.py <candidate-root>            dry run
    promote_rrdm_23a.py <candidate-root> --apply    back up, promote, verify

<candidate-root> is the QCS_QUALIFIED_OUTPUT_ROOT of a run_semester.py 2026S2
+ qualify_site.py PLES --sem 2025S2 candidate run. Every 2026S2 site folder
must be NEW in the active archive (the run refuses to overwrite one). The one
existing folder, HOBO\\qualified\\2025S2\\PLES, is first copied whole to
DATABASE\\_deleted\\rrdm23a_<stamp>\\original\\... and every file there is
SHA-256-verified before the active folder is replaced. qualified_index.csv is
backed up beside it; rebuild the index afterwards with build_index.py (which
runs the mandatory integrity sweep).

Provenance: the candidate blocks carry the raw semester as 'campaign'; the
promoted blocks name the field campaign instead, as the 2026S1 products do,
and the requalified PLES block records when and where its predecessor went.
"""
import datetime as dt
import hashlib
import shutil
import sys
from pathlib import Path

DB = Path(r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE")
HOBO_SITES = ["ESQNORTE", "ESQRODO", "ESQSUL", "PAB3", "PLES", "PNOR", "TIM2"]
NEW = [f"HOBO/qualified/2026S2/{s}" for s in HOBO_SITES] + ["SEAGUARD/qualified/2026S2/CENTROIDE13"]
REPLACED = "HOBO/qualified/2025S2/PLES"
CAMPAIGN = {"2026S2": "RRDM 23a SET 2026",
            "2025S2": "RRDM 21a SET 2025 (HOBO1) | RRDM 23a SET 2026 (HOBO3, recovered 2026-09-22)"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree_hashes(root):
    return {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def patch_provenance(folder, sem, extra=""):
    p = folder / "provenance.txt"
    text = p.read_text(encoding="utf-8")
    old = "    campaign : %s\n" % sem
    if old not in text:
        raise SystemExit("unexpected provenance (no '%s'): %s" % (old.strip(), p))
    p.write_text(text.replace(old, "    campaign : %s\n" % CAMPAIGN[sem]).rstrip("\n") + extra + "\n\n",
                 encoding="utf-8")


def main(cand, apply):
    assert cand.is_dir() and DB.is_dir(), (cand, DB)
    for rel in NEW + [REPLACED]:
        if not (cand / rel).is_dir():
            raise SystemExit("candidate folder missing: %s" % rel)
    for rel in NEW:
        if (DB / rel).exists():
            raise SystemExit("active folder already exists, refusing to overwrite: %s" % rel)
    if not (DB / REPLACED).is_dir():
        raise SystemExit("active folder to replace is missing: %s" % REPLACED)
    print("new folders: %d | replaced: %s" % (len(NEW), REPLACED))
    if not apply:
        print("dry run: nothing written")
        return

    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = DB / "_deleted" / ("rrdm23a_" + stamp)
    orig = backup / "original" / REPLACED
    shutil.copytree(DB / REPLACED, orig)
    shutil.copy2(DB / "qualified_index.csv", backup / "qualified_index.before.csv")
    if tree_hashes(orig) != tree_hashes(DB / REPLACED):
        raise SystemExit("backup verification failed; nothing replaced: %s" % orig)
    print("backup verified: %s (%d files)" % (orig, len(tree_hashes(orig))))

    # stage locally patched copies so the candidate itself stays as produced
    work = backup / "promoted_copy"
    for rel in NEW + [REPLACED]:
        shutil.copytree(cand / rel, work / rel)
    for rel in NEW:
        patch_provenance(work / rel, "2026S2")
    patch_provenance(work / REPLACED, "2025S2",
                     "\n    requalified_on : %s\n    requalified_for : HOBO3_PLES_220325_220926 added as a "
                     "replicate (owner, 2026-11-12)\n    requalification_backup : %s"
                     % (dt.datetime.now().isoformat(timespec="seconds"), orig))

    shutil.rmtree(DB / REPLACED)
    for rel in NEW + [REPLACED]:
        shutil.copytree(work / rel, DB / rel)
        if tree_hashes(work / rel) != tree_hashes(DB / rel):
            raise SystemExit("promotion verification failed: %s (backup at %s)" % (rel, orig))
        print("promoted and verified: %s (%d files)" % (rel, len(tree_hashes(DB / rel))))
    print("backup root:", backup)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]), "--apply" in sys.argv)
