# -*- coding: utf-8 -*-
r"""Remove special collections and normalize both raw trees by semester.

The active corpus becomes::

    DATABASE\SEAGUARD\raw\<YEAR>S<1|2>\<SITE>\...
    DATABASE\HOBO\raw\<YEAR>S<1|2>\<SITE>\...

Several Seaguard field campaigns can belong to one semester. Their site trees
are merged only after proving that no two source files resolve to the same
case-insensitive destination path. File contents are never rewritten.

``_EXPERIMENTOS`` and ``_PISCINAS`` are outside the monitoring corpus. Their
raw and qualified directories are moved into the dated recovery area rather
than permanently deleted because the share has no recycle bin.

Every affected file is SHA-256 fingerprinted into a manifest before the first
move and rechecked at its destination. The script is intentionally gated to the
measured 2026-08-25 state; an unexpected count aborts before mutation.

Usage::

    reorganize_raw_semesters.py --dry-run
    reorganize_raw_semesters.py --apply
    reorganize_raw_semesters.py --verify-existing
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import stat
from pathlib import Path


ROOT = Path(r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE")
TRASH_ROOT = ROOT / "_deleted" / "20260825" / "special_collections"
MANIFEST = ROOT / "_deleted" / "20260825" / "semester_raw_reorganization.csv"
VERIFIED_MARKER = MANIFEST.with_suffix(".verified.txt")
SPECIAL_COLLECTIONS = frozenset({"_EXPERIMENTOS", "_PISCINAS"})
SEMESTER_PATTERN = re.compile(r"\d{4}S[12]")

EXPECTED_CAMPAIGNS = {"SEAGUARD": 18, "HOBO": 15}
EXPECTED_ACTIVE_RAW_FILES = 1_177
EXPECTED_ACTIVE_RAW_BYTES = 137_944_422
EXPECTED_SPECIAL_DIRS = 9
EXPECTED_SPECIAL_FILES = 320
EXPECTED_SPECIAL_BYTES = 23_386_788
EXPECTED_SPECIAL_PRODUCTS = 21

MONTHS = {
    "JAN": 1, "JANEIRO": 1,
    "FEV": 2, "FEVEREIRO": 2,
    "MAR": 3, "MARÇO": 3,
    "ABR": 4, "ABRIL": 4,
    "MAI": 5, "MAIO": 5,
    "JUN": 6, "JUNHO": 6,
    "JUL": 7, "JULHO": 7,
    "AGO": 8, "AGOSTO": 8,
    "SET": 9, "SETEMBRO": 9,
    "OUT": 10, "OUTUBRO": 10,
    "NOV": 11, "NOVEMBRO": 11,
    "DEZ": 12, "DEZEMBRO": 12,
}


def semester(name: str) -> str | None:
    """Map a field-campaign label to the canonical semester folder."""
    if SEMESTER_PATTERN.fullmatch(name):
        return name
    year = re.search(r"(?:19|20)\d{2}", name)
    words = re.findall(r"[A-ZÇÃÁÉÍÓÚ]+", name.upper())
    month = next((MONTHS[word] for word in words if word in MONTHS), None)
    if year is None or month is None:
        return None
    return "%sS%d" % (year.group(0), 1 if month <= 6 else 2)


def relative(path: Path) -> str:
    """Return and validate a corpus-relative path."""
    return str(path.relative_to(ROOT))


def filesystem_path(path: Path) -> Path:
    """Use Windows' extended UNC form so verification survives 260-char paths."""
    text = str(path)
    if os.name == "nt" and text.startswith("\\\\") and not text.startswith("\\\\?\\"):
        return Path("\\\\?\\UNC\\" + text[2:])
    return path


def is_reparse(path: Path) -> bool:
    """Detect links and Windows junction/reparse points without traversing."""
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def walk_files(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: str(path).casefold(),
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def special_roots() -> list[Path]:
    """Return only topmost special-collection directories in active lanes."""
    found = []
    for family in ("SEAGUARD", "HOBO"):
        for lane in ("raw", "qualified"):
            base = ROOT / family / lane
            for current, directories, _files in os.walk(base):
                current_path = Path(current)
                for name in list(directories):
                    if name in SPECIAL_COLLECTIONS:
                        found.append(current_path / name)
                        directories.remove(name)
    return sorted(found, key=lambda path: str(path).casefold())


def campaign_roots() -> dict[str, list[Path]]:
    roots: dict[str, list[Path]] = {}
    for family in ("SEAGUARD", "HOBO"):
        raw = ROOT / family / "raw"
        roots[family] = sorted(
            (path for path in raw.iterdir()
             if path.is_dir()
             and not path.name.startswith("_")
             and not SEMESTER_PATTERN.fullmatch(path.name)),
            key=lambda path: path.name.casefold(),
        )
    return roots


def validate_roots(special: list[Path], campaigns: dict[str, list[Path]]) -> None:
    if str(ROOT) != r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE":
        raise RuntimeError("Unexpected corpus root constant: %s" % ROOT)
    if not ROOT.is_dir():
        raise RuntimeError("Corpus root is unavailable: %s" % ROOT)
    if len(special) != EXPECTED_SPECIAL_DIRS:
        raise RuntimeError(
            "Expected %d special directories, found %d."
            % (EXPECTED_SPECIAL_DIRS, len(special)))
    for family, expected in EXPECTED_CAMPAIGNS.items():
        if len(campaigns[family]) != expected:
            raise RuntimeError(
                "Expected %d %s campaign directories, found %d."
                % (expected, family, len(campaigns[family])))
    for source in special + [path for values in campaigns.values() for path in values]:
        if is_reparse(source):
            raise RuntimeError("Refusing a reparse-point source: %s" % source)
        for path in source.rglob("*"):
            if is_reparse(path):
                raise RuntimeError("Refusing a nested reparse point: %s" % path)


def build_manifest(
        special: list[Path], campaigns: dict[str, list[Path]],
) -> tuple[list[dict[str, object]], dict[Path, list[Path]]]:
    rows: list[dict[str, object]] = []
    directories: dict[Path, list[Path]] = {}
    destination_keys: set[str] = set()

    for source_root in special:
        destination_root = TRASH_ROOT / source_root.relative_to(ROOT)
        if destination_root.exists():
            raise RuntimeError("Recovery destination already exists: %s" % destination_root)
        for source in walk_files(source_root):
            destination = destination_root / source.relative_to(source_root)
            key = str(destination).casefold()
            if key in destination_keys:
                raise RuntimeError("Duplicate recovery destination: %s" % destination)
            destination_keys.add(key)
            rows.append({
                "operation": "exclude_special_collection",
                "source": relative(source),
                "destination": relative(destination),
                "size_bytes": source.stat().st_size,
                "sha256": sha256(source),
            })

    for family, source_roots in campaigns.items():
        raw = ROOT / family / "raw"
        directories[raw] = []
        for source_root in source_roots:
            tag = semester(source_root.name)
            if tag is None:
                raise RuntimeError("Could not derive semester from: %s" % source_root)
            destination_root = raw / tag
            directories[raw].extend(
                destination_root / path.relative_to(source_root)
                for path in source_root.rglob("*") if path.is_dir())
            for source in walk_files(source_root):
                destination = destination_root / source.relative_to(source_root)
                key = str(destination).casefold()
                if key in destination_keys:
                    raise RuntimeError("Raw merge collision: %s" % destination)
                if destination.exists():
                    raise RuntimeError("Raw destination already exists: %s" % destination)
                destination_keys.add(key)
                rows.append({
                    "operation": "normalize_raw_semester",
                    "source": relative(source),
                    "destination": relative(destination),
                    "size_bytes": source.stat().st_size,
                    "sha256": sha256(source),
                })
    return rows, directories


def validate_counts(rows: list[dict[str, object]]) -> None:
    special = [row for row in rows if row["operation"] == "exclude_special_collection"]
    active = [row for row in rows if row["operation"] == "normalize_raw_semester"]
    special_products = sum(
        str(row["source"]).lower().endswith(("_qlf.csv", "_qlf.xlsx"))
        for row in special)
    observed = {
        "active raw files": (len(active), EXPECTED_ACTIVE_RAW_FILES),
        "active raw bytes": (
            sum(int(row["size_bytes"]) for row in active), EXPECTED_ACTIVE_RAW_BYTES),
        "special files": (len(special), EXPECTED_SPECIAL_FILES),
        "special bytes": (
            sum(int(row["size_bytes"]) for row in special), EXPECTED_SPECIAL_BYTES),
        "special qualified products": (special_products, EXPECTED_SPECIAL_PRODUCTS),
    }
    mismatches = [
        "%s: expected %s, found %s" % (label, expected, actual)
        for label, (actual, expected) in observed.items() if actual != expected]
    if mismatches:
        raise RuntimeError("Measured corpus state changed:\n  " + "\n  ".join(mismatches))


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


def apply_moves(
        rows: list[dict[str, object]], special: list[Path],
        campaigns: dict[str, list[Path]], directories: dict[Path, list[Path]],
) -> None:
    for source_root in special:
        destination_root = TRASH_ROOT / source_root.relative_to(ROOT)
        destination_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_root), str(destination_root))

    for _raw, destinations in directories.items():
        for destination in sorted(set(destinations), key=lambda path: len(path.parts)):
            destination.mkdir(parents=True, exist_ok=True)

    for row in rows:
        if row["operation"] != "normalize_raw_semester":
            continue
        source = ROOT / str(row["source"])
        destination = ROOT / str(row["destination"])
        if not source.is_file() or destination.exists():
            raise RuntimeError(
                "Move precondition failed: %s -> %s" % (source, destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))

    for source_root in [path for values in campaigns.values() for path in values]:
        for current, directories_here, files_here in os.walk(source_root, topdown=False):
            if directories_here or files_here:
                # os.walk's cached lists can include directories removed lower
                # down, so the filesystem is checked directly before removal.
                if any(Path(current).iterdir()):
                    raise RuntimeError("Source campaign is not empty: %s" % current)
            Path(current).rmdir()


def verify(rows: list[dict[str, object]]) -> None:
    for number, row in enumerate(rows, start=1):
        source = ROOT / str(row["source"])
        destination = ROOT / str(row["destination"])
        source_io = filesystem_path(source)
        destination_io = filesystem_path(destination)
        if source_io.exists():
            raise RuntimeError("Source still exists after move: %s" % source)
        if not destination_io.is_file():
            raise RuntimeError("Destination is missing after move: %s" % destination)
        if destination_io.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError("Destination size changed: %s" % destination)
        if sha256(destination_io) != row["sha256"]:
            raise RuntimeError("Destination hash changed: %s" % destination)
        if number % 100 == 0:
            print("Verified %d/%d files..." % (number, len(rows)), flush=True)

    for family in ("SEAGUARD", "HOBO"):
        top = [path.name for path in (ROOT / family / "raw").iterdir()
               if path.is_dir()]
        unexpected = [name for name in top if not SEMESTER_PATTERN.fullmatch(name)]
        if unexpected:
            raise RuntimeError(
                "%s raw still has non-semester directories: %s"
                % (family, ", ".join(sorted(unexpected))))
    if special_roots():
        raise RuntimeError("Special collection directories remain in active lanes.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify-existing", action="store_true")
    args = parser.parse_args()

    if args.verify_existing:
        if not MANIFEST.is_file():
            raise RuntimeError("Recovery manifest is missing: %s" % MANIFEST)
        with MANIFEST.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != EXPECTED_ACTIVE_RAW_FILES + EXPECTED_SPECIAL_FILES:
            raise RuntimeError("Unexpected recovery-manifest row count: %d" % len(rows))
        verify(rows)
        VERIFIED_MARKER.write_text(
            "Verified %d moved files against size and SHA-256.\n" % len(rows),
            encoding="utf-8")
        print("Verified %d moved files from the existing recovery manifest."
              % len(rows), flush=True)
        return 0

    special = special_roots()
    campaigns = campaign_roots()
    validate_roots(special, campaigns)
    print("Fingerprinting the planned corpus operation...", flush=True)
    rows, directories = build_manifest(special, campaigns)
    validate_counts(rows)
    active = sum(row["operation"] == "normalize_raw_semester" for row in rows)
    excluded = len(rows) - active
    print(
        "Plan: %d active raw files normalized; %d special files removed from "
        "active lanes (%d qualified products)."
        % (active, excluded, EXPECTED_SPECIAL_PRODUCTS), flush=True)
    for family, sources in campaigns.items():
        tags = sorted({semester(source.name) for source in sources})
        print("%s: %d campaign folders -> %d semester folders (%s)"
              % (family, len(sources), len(tags), ", ".join(tags)), flush=True)
    if args.dry_run:
        print("Dry run complete; nothing was changed.", flush=True)
        return 0

    write_manifest(rows)
    print("Recovery manifest written: %s" % MANIFEST, flush=True)
    apply_moves(rows, special, campaigns, directories)
    verify(rows)
    VERIFIED_MARKER.write_text(
        "Verified %d moved files against size and SHA-256.\n" % len(rows),
        encoding="utf-8")
    print("Verified %d moved files; active corpus reorganization complete."
          % len(rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
