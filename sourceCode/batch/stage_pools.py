# -*- coding: utf-8 -*-
"""Stage the pool ('piscina') data of every expedition into the DATABASE raw
lanes as ORDINARY SITES (v14.1.0; owner decisions 2026-11-12):

  * inside the pool  -> site PISCINA_SGOM / PISCINA_PLES (HOBO and Seaguard);
  * the Seaguard outside the pool (FORA, the control) -> the site itself,
    SGOM / PLES, as the HOBO FORA loggers already are;
  * the unlabelled SGOM pool loggers (18a 'Experimento Piscina', 22a
    'PISCINA SGOM') were inside the pool; 19a Pis1/Pis2 are replicates.

    stage_pools.py            dry run: prints the plan, writes nothing
    stage_pools.py --apply    copies, verifies, writes the manifest

Semester = the campaign that RECOVERED the loggers (the corpus rule).
shutil.copy2 keeps each file's save time (the native-.hobo guard reads it);
every copy is SHA-256- and mtime-verified; an existing destination is never
overwritten (identical bytes are skipped, different bytes stop the run). The
field archive is only read. Not staged: byte-identical second copies, the
22a Seaguard CSV exports (their native sessions are staged), the HOBO FORA
loggers (already in the monitoring sites) and the field-note .txt files
(recorded in CORPUS_LOG instead).

Manifest: diagnostics/abrolhos2_sweep_20261112/staging_pools_manifest.csv.
Anaconda base interpreter; run from sourceCode\\.
"""
import csv
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

import QCS_DataHandler as dh  # noqa: E402

SRC = Path(r"\\Abrolhos2\EXPEDIÇÕES\RRDM")
DB = Path(r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE")
MANIFEST = (Path(__file__).resolve().parents[2] / "diagnostics" / "abrolhos2_sweep_20261112"
            / "staging_pools_manifest.csv")

C18 = "RRDM 18a MAR 2024/SEBASTIÃO GOMES - A2/Experimento Piscina/ZHOBO"
C19 = "RRDM 19a SET 2024/PISCINAS"
C20 = "RRDM 20a MAR 2025/PISCINAS/FERNANDO"
C22 = "RRDM 22a MAR 2026"
C23 = "RRDM 23a SET 2026/Áreas A e B/Área A/PISCINAS"


def hobo(sem, site, rel, sub):
    return (rel, "HOBO/raw/%s/%s/%s" % (sem, site, sub))


def session(sem, site, rel_dir, name):
    return [("%s/%s/%s" % (rel_dir, name, f),
             "SEAGUARD/raw/%s/%s/FUNDEIO/DATA/SENSORES/%s" % (sem, site, name))
            for f in ("Data000.bin", "Config.xml", "Layout.xml")]


COPIES = [
    # 2024S1 (18a): HOBO2's export holds 3 samples and its binary does not decode
    hobo("2024S1", "PISCINA_SGOM", C18 + "/HOBO1_SGOM_PISCINA_out2023_mar2024.hobo", "bruto"),
    hobo("2024S1", "PISCINA_SGOM", C18 + "/HOBO2_SGOM_PISCINA_out2023_mar2024.hobo", "bruto"),
    hobo("2024S1", "PISCINA_SGOM", C18 + "/HOBO1_SGOM_PISCINA_out2023_mar2024.csv", "planilha"),
    hobo("2024S1", "PISCINA_SGOM", C18 + "/HOBO2_SGOM_PISCINA_out2023_mar2024.csv", "planilha"),
    # 2024S2 (19a): the PLES pool loggers are misnamed *_SGOM_*; the folder decides
    hobo("2024S2", "PISCINA_PLES", C19 + "/PLES/DENTRO/HOBO (Dentro)/HOBO1_SGOM_PISCINA_300324_100924.hobo", "bruto"),
    hobo("2024S2", "PISCINA_PLES", C19 + "/PLES/DENTRO/HOBO (Dentro)/HOBO2_SGOM_PISCINA_300324_100924.hobo", "bruto"),
    hobo("2024S2", "PISCINA_PLES", C19 + "/PLES/DENTRO/HOBO (Dentro)/HOBO1_SGOM_PISCINA_300324_100924.csv", "planilha"),
    hobo("2024S2", "PISCINA_PLES", C19 + "/PLES/DENTRO/HOBO (Dentro)/HOBO2_SGOM_PISCINA_300324_100924.csv", "planilha"),
    hobo("2024S2", "PISCINA_SGOM", C19 + "/SGOM/DENTRO/HOBO (Dentro)/SGOM_Pis1_290324_080924.hobo", "bruto"),
    hobo("2024S2", "PISCINA_SGOM", C19 + "/SGOM/DENTRO/HOBO (Dentro)/SGOM_Pis2_290324_080924.hobo", "bruto"),
    hobo("2024S2", "PISCINA_SGOM", C19 + "/SGOM/DENTRO/HOBO (Dentro)/SGOM_Pis1_290324_080924.csv", "planilha"),
    hobo("2024S2", "PISCINA_SGOM", C19 + "/SGOM/DENTRO/HOBO (Dentro)/SGOM_Pis2_290324_080924.csv", "planilha"),
    *session("2024S2", "PISCINA_PLES", C19 + "/PLES/Seaguard (Dentro)", "5650-2104-0-2024-09-10T13-10-00.051Z"),
    # 2025S1 (20a)
    hobo("2025S1", "PISCINA_SGOM", C20 + "/SGOM/DENTRO/HOBOs/HOBO1_PISCINA_SGOM_08092024_21032025.hobo", "bruto"),
    hobo("2025S1", "PISCINA_SGOM", C20 + "/SGOM/DENTRO/HOBOs/HOBO2_PISCINA_SGOMES_080924_210325.hobo", "bruto"),
    hobo("2025S1", "PISCINA_SGOM", C20 + "/SGOM/DENTRO/HOBOs/HOBO1_PISCINA_SGOM_08092024_21032025.xlsx", "planilha"),
    hobo("2025S1", "PISCINA_SGOM", C20 + "/SGOM/DENTRO/HOBOs/HOBO2_PISCINA_SGOMES_080924_210325.xlsx", "planilha"),
    hobo("2025S1", "PISCINA_PLES", C20 + "/PLES/DENTRO/HOBOs/HOBO1_PLES_PISCINA_100924_220325.hobo", "bruto"),
    hobo("2025S1", "PISCINA_PLES", C20 + "/PLES/DENTRO/HOBOs/HOBO2_PLES_PISCINA_100924_220325.hobo", "bruto"),
    hobo("2025S1", "PISCINA_PLES", C20 + "/PLES/DENTRO/HOBOs/HOBO1_PLES_PISCINA_100924_220325.xlsx", "planilha"),
    hobo("2025S1", "PISCINA_PLES", C20 + "/PLES/DENTRO/HOBOs/HOBO2_PLES_PISCINA_100924_220325.xlsx", "planilha"),
    # 2026S1 (22a)
    hobo("2026S1", "PISCINA_PLES", C22 + "/HOBOs/PISCINA PLES/DENTRO/HOBO1_PISCINA_PLES_220325_160326.xlsx", "planilha"),
    hobo("2026S1", "PISCINA_SGOM", C22 + "/HOBOs/PISCINA SGOM/HOBO1_SGOM_PISCINA_210325.hobo", "bruto"),
    hobo("2026S1", "PISCINA_SGOM", C22 + "/HOBOs/PISCINA SGOM/HOBO2_SGOM_PISCINA_210325.hobo", "bruto"),
    hobo("2026S1", "PISCINA_SGOM", C22 + "/HOBOs/PISCINA SGOM/HOBO1_SGOM_PISCINA_210325.xlsx", "planilha"),
    hobo("2026S1", "PISCINA_SGOM", C22 + "/HOBOs/PISCINA SGOM/HOBO2_SGOM_PISCINA_210325.xlsx", "planilha"),
    *session("2026S1", "PISCINA_PLES", C22 + "/Seaguard/Piscinas/DENTRO/PLES", "5650-2104-0-2026-03-16T18-01-00.043Z"),
    (C22 + "/Seaguard/Piscinas/DENTRO/PLES/PISCINA_PLES_CO2_160326_170326.txt",
     "SEAGUARD/raw/2026S1/PISCINA_PLES/FUNDEIO/MINICO2"),
    *session("2026S1", "PISCINA_SGOM", C22 + "/Seaguard/Piscinas/DENTRO/SGOM", "5650-2104-0-2026-03-18T12-01-00.044Z"),
    (C22 + "/Seaguard/Piscinas/DENTRO/SGOM/PISCINA_SGOMES_CO2_180326_190326.txt",
     "SEAGUARD/raw/2026S1/PISCINA_SGOM/FUNDEIO/MINICO2"),
    *session("2026S1", "PLES", C22 + "/Seaguard/Piscinas/FORA/PLES", "5650-2097-0-2026-03-16T18-01-00.007Z"),
    *session("2026S1", "SGOM", C22 + "/Seaguard/Piscinas/FORA/SGOM", "5650-2097-0-2026-03-18T12-01-00.046Z"),
    # 2026S2 (23a)
    hobo("2026S2", "PISCINA_PLES", C23 + "/PLES/DENTRO/HOBO/HOBO1_PISCINA_PLES_230926.hobo", "bruto"),
    hobo("2026S2", "PISCINA_PLES", C23 + "/PLES/DENTRO/HOBO/HOBO2_PISCINA_PLES_230926.hobo", "bruto"),
    hobo("2026S2", "PISCINA_PLES", C23 + "/PLES/DENTRO/HOBO/HOBO1_PISCINA_PLES_230926.xlsx", "planilha"),
    hobo("2026S2", "PISCINA_PLES", C23 + "/PLES/DENTRO/HOBO/HOBO2_PISCINA_PLES_230926.xlsx", "planilha"),
    hobo("2026S2", "PISCINA_SGOM", C23 + "/SGOM/DENTRO/HOBO/HOBO1_PISCINA_SGOMES_180326_260926.hobo", "bruto"),
    hobo("2026S2", "PISCINA_SGOM", C23 + "/SGOM/DENTRO/HOBO/HOBO2_PISCINA_SGOMES_180326_260926.hobo", "bruto"),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(apply):
    assert SRC.is_dir() and DB.is_dir(), (SRC, DB)
    rows = []
    for rel, dest_dir in COPIES:
        src = SRC / rel
        assert src.is_file(), src
        rows.append({"source": str(src), "dest": str(DB / dest_dir / src.name), "bytes": src.stat().st_size,
                     "sha256": sha256(src), "mtime": pd.Timestamp(src.stat().st_mtime, unit="s"), "status": ""})
    assert len({r["dest"] for r in rows}) == len(rows), "two sources map to one destination"
    for r in rows:                                   # what the Seaguard sessions are
        if r["source"].endswith("Data000.bin"):
            kind, hours, step = dh.detect_seaguard_data_type(r["source"])
            print("session %s: %s, %.1f h at %s s" % (Path(r["source"]).parent.name, kind, hours or 0, step))
    for r in rows:
        dest = Path(r["dest"])
        if dest.exists():
            if sha256(dest) == r["sha256"]:
                r["status"] = "already staged (identical)"
                continue
            raise SystemExit("destination exists with different bytes: %s" % dest)
        if not apply:
            r["status"] = "would copy"
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = Path(r["source"])
        shutil.copy2(src, dest)
        if sha256(dest) != r["sha256"]:
            raise SystemExit("hash mismatch after copy: %s" % dest)
        if abs(dest.stat().st_mtime - src.stat().st_mtime) > 2:
            raise SystemExit("mtime not preserved: %s" % dest)
        r["status"] = "copied, sha256 and mtime verified"
    for r in rows:
        print("%-36s %s" % (r["status"], r["dest"].replace(str(DB), "DATABASE")))
    print("files:", len(rows))
    if apply:
        with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print("manifest:", MANIFEST)


if __name__ == "__main__":
    main("--apply" in sys.argv)
