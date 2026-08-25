# -*- coding: utf-8 -*-
r"""Remove the five Seaguard PISCINA_* sites from the active corpus.

Removal is recoverable: each raw and qualified site directory is moved to
``DATABASE\_deleted\20260825\seaguard_pool_sites``. A manifest containing the
original path, recovery path, size and SHA-256 is written before any move and
verified afterwards. The script is gated to the measured 2026-08-25 state.

Usage::

    remove_seaguard_pool_sites.py --dry-run
    remove_seaguard_pool_sites.py --apply
    remove_seaguard_pool_sites.py --verify-existing
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
RECOVERY_ROOT = ROOT / "_deleted" / "20260825" / "seaguard_pool_sites"
MANIFEST = ROOT / "_deleted" / "20260825" / "seaguard_pool_sites_removal.csv"
VERIFIED_MARKER = MANIFEST.with_suffix(".verified.txt")
SITES = (
    ("2024S2", "PISCINA_PLES_DENTRO"),
    ("2026S1", "PISCINA_PLES_DENTRO"),
    ("2026S1", "PISCINA_PLES_FORA"),
    ("2026S1", "PISCINA_SGOM_DENTRO"),
    ("2026S1", "PISCINA_SGOM_FORA"),
)
EXPECTED_DIRECTORIES = 10
EXPECTED_FILES = 120
EXPECTED_BYTES = 25_297_340
EXPECTED_PRODUCTS = 5
EXPECTED_PRODUCT_ROWS = 6_675


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


def targets() -> list[Path]:
    return [
        ROOT / "SEAGUARD" / lane / semester / site
        for lane in ("raw", "qualified")
        for semester, site in SITES
    ]


def is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def qlf_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader)
        return sum(1 for _row in reader)


def build_manifest() -> tuple[list[dict[str, object]], list[Path]]:
    roots = targets()
    if len(roots) != EXPECTED_DIRECTORIES:
        raise RuntimeError("Unexpected target-directory count: %d" % len(roots))
    rows = []
    products = []
    for root in roots:
        try:
            root.relative_to(ROOT / "SEAGUARD")
        except ValueError as exc:
            raise RuntimeError("Target escaped Seaguard: %s" % root) from exc
        if not root.is_dir():
            raise RuntimeError("Expected target is missing: %s" % root)
        destination_root = RECOVERY_ROOT / root.relative_to(ROOT)
        if destination_root.exists():
            raise RuntimeError("Recovery destination already exists: %s" % destination_root)
        for path in [root, *root.rglob("*")]:
            if is_reparse(path):
                raise RuntimeError("Refusing a reparse-point target: %s" % path)
            if not path.is_file():
                continue
            if path.name.lower().endswith(("_qlf.csv", "_qlf.xlsx")):
                products.append(path)
            destination = destination_root / path.relative_to(root)
            rows.append({
                "source": str(path.relative_to(ROOT)),
                "destination": str(destination.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    observed = {
        "files": (len(rows), EXPECTED_FILES),
        "bytes": (sum(int(row["size_bytes"]) for row in rows), EXPECTED_BYTES),
        "qualified products": (len(products), EXPECTED_PRODUCTS),
        "qualified product rows": (
            sum(qlf_rows(path) for path in products), EXPECTED_PRODUCT_ROWS),
    }
    differences = [
        "%s: expected %d, found %d" % (name, expected, actual)
        for name, (actual, expected) in observed.items() if actual != expected]
    if differences:
        raise RuntimeError("Measured pool-site state changed:\n  " + "\n  ".join(differences))
    return rows, roots


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


def apply_moves(roots: list[Path]) -> None:
    for source in roots:
        destination = RECOVERY_ROOT / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))


def verify(rows: list[dict[str, object]]) -> None:
    for number, row in enumerate(rows, start=1):
        source = ROOT / str(row["source"])
        destination = ROOT / str(row["destination"])
        if filesystem_path(source).exists():
            raise RuntimeError("Source still exists: %s" % source)
        destination_io = filesystem_path(destination)
        if not destination_io.is_file():
            raise RuntimeError("Recovery file is missing: %s" % destination)
        if destination_io.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError("Recovery-file size changed: %s" % destination)
        if sha256(destination) != row["sha256"]:
            raise RuntimeError("Recovery-file hash changed: %s" % destination)
        if number % 25 == 0:
            print("Verified %d/%d files..." % (number, len(rows)), flush=True)


def load_manifest() -> list[dict[str, object]]:
    if not MANIFEST.is_file():
        raise RuntimeError("Removal manifest is missing: %s" % MANIFEST)
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
        print("Verified the existing Seaguard pool-site removal.", flush=True)
        return 0

    print("Fingerprinting the five Seaguard pool sites...", flush=True)
    rows, roots = build_manifest()
    print("Plan: %d directories, %d files, %d bytes, %d products / %d rows."
          % (len(roots), len(rows), sum(int(row["size_bytes"]) for row in rows),
             EXPECTED_PRODUCTS, EXPECTED_PRODUCT_ROWS), flush=True)
    if args.dry_run:
        print("Dry run complete; nothing was changed.", flush=True)
        return 0
    write_manifest(rows)
    print("Recovery manifest written: %s" % MANIFEST, flush=True)
    apply_moves(roots)
    verify(rows)
    mark_verified(rows)
    print("Seaguard pool sites removed from the active corpus and verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
