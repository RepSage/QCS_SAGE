# -*- coding: utf-8 -*-
"""Promote the validated pool candidate products (v14.1.0) into the archive.

    promote_pools.py <candidate-root>            dry run
    promote_pools.py <candidate-root> --apply    promote, verify

<candidate-root> is the QCS_QUALIFIED_OUTPUT_ROOT of the candidate run
(qualify_site.py per pool site/semester, plus SGOM/PLES 2026S1 with
QCS_SG_ONLY=1). Every destination folder must be NEW in the archive - the
run refuses to overwrite anything. qualified_index.csv is backed up to
DATABASE\\_deleted\\pools_<stamp>\\ first; rebuild it afterwards with
build_index.py (which runs the mandatory integrity sweep).

Provenance: the candidate blocks carry the raw semester as 'campaign'; the
promoted blocks name the field campaign that recovered the loggers, as the
other products do.
"""
import datetime as dt
import hashlib
import shutil
import sys
from pathlib import Path

DB = Path(r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE")
FOLDERS = [
    "HOBO/qualified/2024S1/PISCINA_SGOM",
    "HOBO/qualified/2024S2/PISCINA_SGOM", "HOBO/qualified/2024S2/PISCINA_PLES",
    "HOBO/qualified/2025S1/PISCINA_SGOM", "HOBO/qualified/2025S1/PISCINA_PLES",
    "HOBO/qualified/2026S1/PISCINA_SGOM", "HOBO/qualified/2026S1/PISCINA_PLES",
    "HOBO/qualified/2026S2/PISCINA_SGOM", "HOBO/qualified/2026S2/PISCINA_PLES",
    "SEAGUARD/qualified/2024S2/PISCINA_PLES",
    "SEAGUARD/qualified/2026S1/PISCINA_PLES", "SEAGUARD/qualified/2026S1/PISCINA_SGOM",
    "SEAGUARD/qualified/2026S1/PLES", "SEAGUARD/qualified/2026S1/SGOM",
]
CAMPAIGN = {"2024S1": "RRDM 18a MAR 2024", "2024S2": "RRDM 19a SET 2024",
            "2025S1": "RRDM 20a MAR 2025", "2026S1": "RRDM 22a MAR 2026",
            "2026S2": "RRDM 23a SET 2026"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree_hashes(root):
    return {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def main(cand, apply):
    assert cand.is_dir() and DB.is_dir(), (cand, DB)
    for rel in FOLDERS:
        if not list((cand / rel).glob("*_QLF.csv")):
            raise SystemExit("candidate folder has no product: %s" % rel)
        if (DB / rel).exists():
            raise SystemExit("active folder already exists, refusing to overwrite: %s" % rel)
    extra = sorted({str(p.parent.relative_to(cand)).replace("\\", "/") for p in cand.rglob("*_QLF.csv")}
                   - set(FOLDERS))
    if extra:
        raise SystemExit("candidate holds products outside the plan: %s" % extra)
    print("new folders: %d" % len(FOLDERS))
    if not apply:
        print("dry run: nothing written")
        return
    backup = DB / "_deleted" / ("pools_" + dt.datetime.now().strftime("%Y%m%dT%H%M%S"))
    backup.mkdir(parents=True)
    shutil.copy2(DB / "qualified_index.csv", backup / "qualified_index.before.csv")
    work = backup / "promoted_copy"
    for rel in FOLDERS:
        shutil.copytree(cand / rel, work / rel)
        prov = work / rel / "provenance.txt"
        sem = rel.split("/")[2]
        text = prov.read_text(encoding="utf-8")
        old = "    campaign : %s\n" % sem
        if old not in text:
            raise SystemExit("unexpected provenance: %s" % prov)
        prov.write_text(text.replace(old, "    campaign : %s\n" % CAMPAIGN[sem]), encoding="utf-8")
    for rel in FOLDERS:
        shutil.copytree(work / rel, DB / rel)
        if tree_hashes(work / rel) != tree_hashes(DB / rel):
            raise SystemExit("promotion verification failed: %s" % rel)
        print("promoted and verified: %s (%d files)" % (rel, len(tree_hashes(DB / rel))))
    print("backup root:", backup)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]), "--apply" in sys.argv)
