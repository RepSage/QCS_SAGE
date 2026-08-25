# -*- coding: utf-8 -*-
r"""Give the recovered BURACA_FUNDA session its instrument-declared name.

The 2021S2 scalar binary arrived below an anonymous ``Sensores`` directory.
Its own BXML template identifies the session as
``5650-2097-0-2021-10-01T18-35-10.047Z``. The batch planner requires that
session identity in the folder name, so this script moves the directory to the
canonical name after writing a size/SHA-256 manifest.

Usage::

    normalize_buraca_funda_session.py --dry-run
    normalize_buraca_funda_session.py --apply
    normalize_buraca_funda_session.py --verify-existing
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import stat
import struct
from pathlib import Path


ROOT = Path(r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE")
SESSION_ID = "5650-2097-0-2021-10-01T18-35-10.047Z"
SESSION_PARENT = (
    ROOT / "SEAGUARD" / "raw" / "2021S2" / "BURACA_FUNDA"
    / "PERFIL" / "DATA" / "SENSORES"
)
SOURCE = SESSION_PARENT / "Sensores"
DESTINATION = SESSION_PARENT / SESSION_ID
MANIFEST = (
    ROOT / "_deleted" / "20260825"
    / "buraca_funda_session_normalization.csv"
)
VERIFIED_MARKER = MANIFEST.with_suffix(".verified.txt")
EXPECTED_FILES = 1
EXPECTED_BYTES = 44_902


def filesystem_path(path: Path) -> Path:
    """Use extended UNC paths so verification has no 260-character limit."""
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


def bxml_session_id(path: Path) -> str:
    with filesystem_path(path).open("rb") as handle:
        head = handle.read(0x40)
        if not head.startswith(b"AADIBXML") or len(head) < 0x38:
            raise RuntimeError("Not an AADI BXML session: %s" % path)
        template_offset, _a, _b, _c, template_length, _d, _e = struct.unpack_from(
            "<7I", head, 0x1C)
        handle.seek(template_offset)
        template = handle.read(template_length).decode("utf-8", errors="replace")
    match = re.search(r'<Data\b[^>]*\bSessionID="([^"]+)"', template)
    if not match:
        raise RuntimeError("The AADI session ID is missing: %s" % path)
    return match.group(1)


def is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def build_manifest() -> list[dict[str, object]]:
    if not ROOT.is_dir():
        raise RuntimeError("Corpus root is unavailable: %s" % ROOT)
    if not SOURCE.is_dir():
        raise RuntimeError("Anonymous session directory is missing: %s" % SOURCE)
    if DESTINATION.exists():
        raise RuntimeError("Canonical session destination already exists: %s" % DESTINATION)

    rows = []
    for path in [SOURCE, *SOURCE.rglob("*")]:
        if is_reparse(path):
            raise RuntimeError("Refusing a reparse-point target: %s" % path)
        if not path.is_file():
            continue
        destination = DESTINATION / path.relative_to(SOURCE)
        rows.append({
            "source": str(path.relative_to(ROOT)),
            "destination": str(destination.relative_to(ROOT)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    observed_files = len(rows)
    observed_bytes = sum(int(row["size_bytes"]) for row in rows)
    if observed_files != EXPECTED_FILES or observed_bytes != EXPECTED_BYTES:
        raise RuntimeError(
            "Measured session state changed: expected %d file/%d bytes, found %d/%d."
            % (EXPECTED_FILES, EXPECTED_BYTES, observed_files, observed_bytes))
    binary = SOURCE / "Data000.bin"
    observed_session = bxml_session_id(binary)
    if observed_session != SESSION_ID:
        raise RuntimeError(
            "Instrument session changed: expected %s, found %s."
            % (SESSION_ID, observed_session))
    return rows


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


def load_manifest() -> list[dict[str, object]]:
    if not MANIFEST.is_file():
        raise RuntimeError("Normalization manifest is missing: %s" % MANIFEST)
    with MANIFEST.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_FILES:
        raise RuntimeError("Unexpected manifest row count: %d" % len(rows))
    return rows


def verify(rows: list[dict[str, object]]) -> None:
    for row in rows:
        source = ROOT / str(row["source"])
        destination = ROOT / str(row["destination"])
        if filesystem_path(source).exists():
            raise RuntimeError("Source still exists: %s" % source)
        destination_io = filesystem_path(destination)
        if not destination_io.is_file():
            raise RuntimeError("Destination file is missing: %s" % destination)
        if destination_io.stat().st_size != int(row["size_bytes"]):
            raise RuntimeError("Destination-file size changed: %s" % destination)
        if sha256(destination) != row["sha256"]:
            raise RuntimeError("Destination-file hash changed: %s" % destination)
    if not DESTINATION.is_dir():
        raise RuntimeError("Canonical session directory is missing: %s" % DESTINATION)
    if bxml_session_id(DESTINATION / "Data000.bin") != SESSION_ID:
        raise RuntimeError("The moved binary no longer reports the expected session ID.")


def mark_verified(rows: list[dict[str, object]]) -> None:
    VERIFIED_MARKER.write_text(
        "Verified %d moved file against size, SHA-256 and BXML session ID.\n"
        % len(rows),
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
        print("Verified the existing BURACA_FUNDA session normalization.", flush=True)
        return 0

    print("Fingerprinting the anonymous BURACA_FUNDA session...", flush=True)
    rows = build_manifest()
    print(
        "Plan: %d directory, %d file, %d bytes -> %s."
        % (1, len(rows), sum(int(row["size_bytes"]) for row in rows), SESSION_ID),
        flush=True)
    if args.dry_run:
        print("Dry run complete; nothing was changed.", flush=True)
        return 0

    write_manifest(rows)
    print("Normalization manifest written: %s" % MANIFEST, flush=True)
    shutil.move(str(SOURCE), str(DESTINATION))
    verify(rows)
    mark_verified(rows)
    print("BURACA_FUNDA session normalized and verified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
