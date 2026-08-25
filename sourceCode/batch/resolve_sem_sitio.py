# -*- coding: utf-8 -*-
r"""Resolve every active Seaguard ``_SEM_SITIO`` directory.

The owner identified the raw 2021S2 deployment as ``BURACA_FUNDA``. That raw
directory is moved to the corrected active site path. The 2019S1, 2019S2 and
2020S1 raw and qualified directories cannot be assigned to a site and are
moved recoverably below ``DATABASE\_deleted\20260825``.

A manifest containing operation, original path, destination path, size and
SHA-256 is written before any move and verified afterwards.

Usage::

    resolve_sem_sitio.py --dry-run
    resolve_sem_sitio.py --apply
    resolve_sem_sitio.py --verify-existing
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import stat
from pathlib import Path


ROOT = Path(r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE")
RECOVERY_ROOT = ROOT / "_deleted" / "20260825" / "sem_sitio_unknown_origin"
MANIFEST = ROOT / "_deleted" / "20260825" / "sem_sitio_resolution.csv"
VERIFIED_MARKER = MANIFEST.with_suffix(".verified.txt")
SUCCESSOR_MANIFEST = (
    ROOT / "_deleted" / "20260825"
    / "buraca_funda_session_normalization.csv"
)
UNKNOWN_SEMESTERS = ("2019S1", "2019S2", "2020S1")
REASSIGNED_SEMESTER = "2021S2"
REASSIGNED_SITE = "BURACA_FUNDA"

EXPECTED_DIRECTORIES = 7
EXPECTED_FILES = 110
EXPECTED_BYTES = 7_425_270
EXPECTED_PRODUCTS = 7
EXPECTED_PRODUCT_ROWS = 8_428
EXPECTED_REASSIGNED_FILES = 2
EXPECTED_REASSIGNED_BYTES = 150_438


def filesystem_path(path: Path) -> Path:
    """Use extended UNC paths so recovery verification has no 260-char limit."""
    text = str(path)
    if os.name == "nt" and text.startswith("\\\\") and not text.startswith("\\\\?\\"):
        return Path("\\\\?\\UNC\\" + text[2:])
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with filesystem_path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def qlf_rows(path: Path) -> int:
    with filesystem_path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader)
        return sum(1 for _row in reader)


def operations() -> list[tuple[str, Path, Path]]:
    seaguard = ROOT / "SEAGUARD"
    rows = []
    for lane in ("raw", "qualified"):
        for semester in UNKNOWN_SEMESTERS:
            source = seaguard / lane / semester / "_SEM_SITIO"
            destination = RECOVERY_ROOT / source.relative_to(ROOT)
            rows.append(("exclude_unknown_site", source, destination))
    source = seaguard / "raw" / REASSIGNED_SEMESTER / "_SEM_SITIO"
    destination = seaguard / "raw" / REASSIGNED_SEMESTER / REASSIGNED_SITE
    rows.append(("reassign_site", source, destination))
    return rows


def is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def validate_root() -> None:
    expected = r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE"
    if str(ROOT) != expected:
        raise RuntimeError("Unexpected corpus root constant: %s" % ROOT)
    if not ROOT.is_dir():
        raise RuntimeError("Corpus root is unavailable: %s" % ROOT)


def build_manifest() -> tuple[list[dict[str, object]], list[tuple[str, Path, Path]]]:
    validate_root()
    planned = operations()
    if len(planned) != EXPECTED_DIRECTORIES:
        raise RuntimeError("Unexpected target-directory count: %d" % len(planned))

    rows = []
    products = []
    for operation, source_root, destination_root in planned:
        try:
            source_root.relative_to(ROOT / "SEAGUARD")
        except ValueError as exc:
            raise RuntimeError("Source escaped Seaguard: %s" % source_root) from exc
        if not source_root.is_dir():
            raise RuntimeError("Expected source is missing: %s" % source_root)
        if destination_root.exists():
            raise RuntimeError("Destination already exists: %s" % destination_root)
        for path in [source_root, *source_root.rglob("*")]:
            if is_reparse(path):
                raise RuntimeError("Refusing a reparse-point target: %s" % path)
            if not path.is_file():
                continue
            if path.name.lower().endswith(("_qlf.csv", "_qlf.xlsx")):
                products.append(path)
            destination = destination_root / path.relative_to(source_root)
            rows.append({
                "operation": operation,
                "source": str(path.relative_to(ROOT)),
                "destination": str(destination.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })

    reassigned = [row for row in rows if row["operation"] == "reassign_site"]
    observed = {
        "files": (len(rows), EXPECTED_FILES),
        "bytes": (sum(int(row["size_bytes"]) for row in rows), EXPECTED_BYTES),
        "qualified products": (len(products), EXPECTED_PRODUCTS),
        "qualified product rows": (
            sum(qlf_rows(path) for path in products), EXPECTED_PRODUCT_ROWS),
        "reassigned files": (len(reassigned), EXPECTED_REASSIGNED_FILES),
        "reassigned bytes": (
            sum(int(row["size_bytes"]) for row in reassigned),
            EXPECTED_REASSIGNED_BYTES),
    }
    differences = [
        "%s: expected %d, found %d" % (name, expected, actual)
        for name, (actual, expected) in observed.items() if actual != expected]
    if differences:
        raise RuntimeError("Measured _SEM_SITIO state changed:\n  " + "\n  ".join(differences))
    return rows, planned


def write_manifest(rows: list[dict[str, object]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists() or VERIFIED_MARKER.exists():
        raise RuntimeError("Operation record already exists: %s" % MANIFEST)
    with MANIFEST.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if MANIFEST.stat().st_size == 0:
        raise RuntimeError("Manifest write failed: %s" % MANIFEST)


def apply_moves(planned: list[tuple[str, Path, Path]]) -> None:
    for _operation, source, destination in planned:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))


def verify(rows: list[dict[str, object]]) -> None:
    successors = {}
    if SUCCESSOR_MANIFEST.is_file():
        with SUCCESSOR_MANIFEST.open(newline="", encoding="utf-8-sig") as handle:
            successors = {
                row["source"]: row["destination"]
                for row in csv.DictReader(handle)
            }
    for number, row in enumerate(rows, start=1):
        source = ROOT / str(row["source"])
        destination_relative = str(row["destination"])
        destination = ROOT / destination_relative
        if filesystem_path(source).exists():
            raise RuntimeError("Source still exists: %s" % source)
        destination_io = filesystem_path(destination)
        if not destination_io.is_file() and destination_relative in successors:
            destination = ROOT / successors[destination_relative]
            destination_io = filesystem_path(destination)
        if not destination_io.is_file():
            raise RuntimeError("Destination file is missing: %s" % destination)
        if destination_io.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError("Destination-file size changed: %s" % destination)
        if sha256(destination) != row["sha256"]:
            raise RuntimeError("Destination-file hash changed: %s" % destination)
        if number % 25 == 0:
            print("Verified %d/%d files..." % (number, len(rows)), flush=True)

    for _operation, source, destination in operations():
        if source.exists():
            raise RuntimeError("Source directory still exists: %s" % source)
        if not destination.is_dir():
            raise RuntimeError("Destination directory is missing: %s" % destination)


def load_manifest() -> list[dict[str, object]]:
    if not MANIFEST.is_file():
        raise RuntimeError("Resolution manifest is missing: %s" % MANIFEST)
    with MANIFEST.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_FILES:
        raise RuntimeError("Unexpected manifest row count: %d" % len(rows))
    return rows


def mark_verified(rows: list[dict[str, object]]) -> None:
    VERIFIED_MARKER.write_text(
        "Verified %d moved files against size and SHA-256.\n" % len(rows),
        encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify-existing", action="store_true")
    args = parser.parse_args()

    if args.verify_existing:
        rows = load_manifest()
        verify(rows)
        mark_verified(rows)
        print("Verified the existing _SEM_SITIO resolution.", flush=True)
        return 0

    print("Fingerprinting every active Seaguard _SEM_SITIO directory...", flush=True)
    rows, planned = build_manifest()
    print(
        "Plan: %d directories, %d files, %d bytes, %d products / %d rows; "
        "%d files reassigned to %s."
        % (len(planned), len(rows), sum(int(row["size_bytes"]) for row in rows),
           EXPECTED_PRODUCTS, EXPECTED_PRODUCT_ROWS, EXPECTED_REASSIGNED_FILES,
           REASSIGNED_SITE),
        flush=True)
    if args.dry_run:
        print("Dry run complete; nothing was changed.", flush=True)
        return 0

    write_manifest(rows)
    print("Resolution manifest written: %s" % MANIFEST, flush=True)
    apply_moves(planned)
    verify(rows)
    mark_verified(rows)
    print("_SEM_SITIO resolved and every destination verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
