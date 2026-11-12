# -*- coding: utf-8 -*-
"""Stage the RRDM 23a SET 2026 monitoring data (and the 2025S2 PLES HOBO3 it
brought back) from the field archive into the DATABASE raw lanes.

    stage_rrdm_23a.py            dry run: prints the plan, writes nothing
    stage_rrdm_23a.py --apply    copies, verifies, writes the manifest

Every copy is shutil.copy2, so the file's save time (mtime) survives - the
native-.hobo stale guard in qualify_site.py reads it. Each copy is verified by
SHA-256 and mtime against its source. An existing destination is never
overwritten: identical bytes are reported and skipped, different bytes stop
the run. The field archive is only read.

One DERIVED file is written: the miniCO2 sheet of CENTROIDE13 came as an
.xlsx with the logger's text-export columns; read_co2_file reads the text
export only, so the same rows are written as that text format (header line,
format line, comma-separated rows) beside the untouched .xlsx, and read back
through read_co2_file and compared value by value before it is staged.

Manifest: diagnostics/abrolhos2_sweep_20261112/staging_manifest.csv.
Anaconda base interpreter; run from sourceCode\\.
"""
import csv
import hashlib
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

import QCS_DataHandler as dh  # noqa: E402

SRC = Path(r"\\Abrolhos2\EXPEDIÇÕES\RRDM\RRDM 23a SET 2026")
DB = Path(r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE")
MANIFEST = Path(__file__).resolve().parents[2] / "diagnostics" / "abrolhos2_sweep_20261112" / "staging_manifest.csv"
A, B = "Áreas A e B/Área A", "Áreas A e B/Área B"
H26, H25 = "HOBO/raw/2026S2", "HOBO/raw/2025S2"
C13 = "SEAGUARD/raw/2026S2/CENTROIDE13/FUNDEIO"
FUNDEIO_SRC = "SEAGUARD/CENTROIDE 13/FUNDEIO SEAGUARD"
CO2_XLSX = "miniCO2_centroid13_19a20set2026 - padronizar com uma planilha original de CO2.xlsx"
CO2_TXT = "miniCO2_centroid13_19a20set2026.txt"

# (source relative to SRC, destination folder relative to DB)
COPIES = [
    (f"{A}/ARQUIPELAGO/HOBO/HOBO2_PNOR_A4_150326_290926.hobo", f"{H26}/PNOR/bruto"),
    (f"{A}/PLES/HOBO/HOBO1_PLES_160326_220926.hobo", f"{H26}/PLES/bruto"),
    (f"{A}/PLES/HOBO/HOBO2_PLES_160326_220926.hobo", f"{H26}/PLES/bruto"),
    (f"{A}/PAB3/HOBO/HOBO2_PAB3_A3_110326_270926.hobo", f"{H26}/PAB3/bruto"),
    (f"{A}/SGOM/HOBO/HOBO1_SGOMES_A2_250926.hobo", f"{H26}/SGOM/bruto"),
    (f"{A}/SGOM/HOBO/HOBO1_SGOMES_A2_250926.csv", f"{H26}/SGOM/planilha"),
    # HOBO2_RODORASO_A5_230326_0.hobo is a byte-identical second copy: not staged
    (f"{A}/A5/HOBO/HOBO2_RODORASO_A5_230326.hobo", f"{H26}/RODORASO/bruto"),
    (f"{A}/TIM 2/HOBO/HOBO1_TIM2_A6_210326_retirado150926.hobo", f"{H26}/TIM2/bruto"),
    (f"{A}/TIM 2/HOBO/HOBO2_TIM2_A6_210326.hobo_160926", f"{H26}/TIM2/bruto"),
    (f"{A}/TIM 2/HOBO/HOBO1_TIM2_A6_210326_retirado150926.xlsx", f"{H26}/TIM2/planilha"),
    (f"{A}/TIM 2/HOBO/HOBO2_TIM2_A6_210326_retirado150926.xlsx", f"{H26}/TIM2/planilha"),
    (f"{B}/ESQ NORTE B2/HOBO/HOBO1_ESQNORTE_B2_10032026.hobo", f"{H26}/ESQNORTE/bruto"),
    (f"{B}/ESQ NORTE B2/HOBO/HOBO2_ESQNORTE_B2_10032025.hobo", f"{H26}/ESQNORTE/bruto"),
    (f"{B}/ESQ RODO B1/HOBO/HOBO1_ESQR_B1_10032026.hobo", f"{H26}/ESQRODO/bruto"),
    (f"{B}/ESQ RODO B1/HOBO/HOBO2_ESQR_B1_10032026.hobo", f"{H26}/ESQRODO/bruto"),
    (f"{B}/ESQSUL B4/HOBO/HOBO1_ESQS_B4_080326_021026.hobo", f"{H26}/ESQSUL/bruto"),
    (f"{B}/ESQSUL B4/HOBO/HOBO2_ESQS_B4_080326_021026.hobo", f"{H26}/ESQSUL/bruto"),
    # owner, 2026-11-12: 2025-03-22..2025-09-05 data, verified against HOBO1
    (f"{A}/PLES/HOBO/HOBO3_PLES_220325_220926.hobo", f"{H25}/PLES/bruto"),
    (f"{FUNDEIO_SRC}/fundeio_centroide13_19e20set2026.csv", f"{C13}/EXPORT/SENSORES"),
    (f"{FUNDEIO_SRC}/fundeio_centroide13_ADCP_19e20set2026.csv", f"{C13}/EXPORT/DOPPLER"),
    (f"{FUNDEIO_SRC}/{CO2_XLSX}", f"{C13}/MINICO2"),
]
CO2_COLUMNS = ["Measurement type", "Year", "Month", "Day", "Hour", "Minute", "Second",
               "Reference A/D", "Current A/D", "CO2 (PPM)", "Corrected disolved CO2 (PPM)",
               "Pressure sensor temperature", "Pressure", "IRGA detector temperature",
               "Supply voltage"]
# the logger's own format line, as in every archived CO2 text export
CO2_FORMAT_LINE = "%s,%4.0f,%2.0f,%2.0f,%2.0f,%2.0f,%2.0f,%5.0f,%5.0f,%07.2f,%03.2f,%02.2f,%4.2f,%02.2f,%02.1f"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def derive_co2_txt(xlsx, out):
    """Writes the text export from the sheet; returns the number of rows."""
    x = pd.read_excel(xlsx, header=0)
    if list(x.columns) != CO2_COLUMNS:
        raise SystemExit("unexpected miniCO2 columns: %s" % list(x.columns))
    lines = [",".join(CO2_COLUMNS), CO2_FORMAT_LINE]
    for r in x.itertuples(index=False):
        ints = ["%04d" % r[1]] + ["%02d" % v for v in r[2:7]] + ["%05d" % v for v in r[7:9]]
        two = ["%.2f" % v for v in r[9:14]]
        lines.append(",".join([str(r[0])] + ints + two + ["%.1f" % r[14]]))
    with open(out, "w", encoding="ascii", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    # read it back through the pipeline's reader and compare with the sheet
    back, _msgs = dh.read_co2_file(str(out))
    stamp = pd.to_datetime(dict(year=x["Year"], month=x["Month"], day=x["Day"], hour=x["Hour"],
                                minute=x["Minute"], second=x["Second"]))
    want = pd.DataFrame({"Datetime": stamp, "CO2 Level (ppm)": x["Corrected disolved CO2 (PPM)"].astype(float)})
    want = want.sort_values("Datetime").drop_duplicates("Datetime").reset_index(drop=True)
    if len(back) != len(want) or not (back["Datetime"].values == want["Datetime"].values).all() \
            or not ((back["CO2 Level (ppm)"] - want["CO2 Level (ppm)"]).abs() < 0.005).all():
        raise SystemExit("derived CO2 text does not read back to the sheet's values")
    return len(x)


def main(apply):
    assert SRC.is_dir() and DB.is_dir(), (SRC, DB)
    rows = []
    for rel, dest_dir in COPIES:
        src = SRC / rel
        assert src.is_file(), src
        dest = DB / dest_dir / src.name
        rows.append({"source": str(src), "dest": str(dest), "kind": "copy", "bytes": src.stat().st_size,
                     "sha256": sha256(src), "mtime": pd.Timestamp(src.stat().st_mtime, unit="s"),
                     "status": ""})
    tmp = Path(tempfile.mkdtemp(prefix="co2_"))
    n_co2 = derive_co2_txt(SRC / FUNDEIO_SRC / CO2_XLSX, tmp / CO2_TXT)
    rows.append({"source": "derived from " + str(SRC / FUNDEIO_SRC / CO2_XLSX), "kind": "derived",
                 "dest": str(DB / C13 / "MINICO2" / CO2_TXT), "bytes": (tmp / CO2_TXT).stat().st_size,
                 "sha256": sha256(tmp / CO2_TXT), "mtime": "", "status": "",
                 "_local": tmp / CO2_TXT})
    print("derived CO2 text: %d rows, read back through read_co2_file and matched" % n_co2)

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
        src = r.pop("_local", None) or Path(r["source"])
        shutil.copy2(src, dest)
        if sha256(dest) != r["sha256"]:
            raise SystemExit("hash mismatch after copy: %s" % dest)
        if r["kind"] == "copy" and abs(dest.stat().st_mtime - src.stat().st_mtime) > 2:
            raise SystemExit("mtime not preserved: %s" % dest)
        r["status"] = "copied, sha256 and mtime verified" if r["kind"] == "copy" else "written, sha256 verified"
    for r in rows:
        r.pop("_local", None)
        print("%-36s %s" % (r["status"], r["dest"].replace(str(DB), "DATABASE")))
    if apply:
        with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["source", "dest", "kind", "bytes", "sha256", "mtime", "status"])
            w.writeheader()
            w.writerows(rows)
        print("manifest:", MANIFEST)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main("--apply" in sys.argv)
