#!/usr/bin/env python3
"""Build a deterministic public release ZIP. No n8n install."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT.parent / "downloads"
VERSION = "0.1.1"
ZIP_NAME = f"Flowgrammer-n8n-Document-Processing-Starter-v{VERSION}.zip"
STAMP = (2026, 9, 8, 0, 0, 0)
ARCHIVE_ROOT = f"n8n"
SKIP_DIR = {"__pycache__", ".git"}
SKIP_SUFFIX = {".pyc", ".DS_Store"}
SKIP_NAMES = {".DS_Store"}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR for part in path.parts):
            continue
        if path.suffix in SKIP_SUFFIX or path.name in SKIP_NAMES:
            continue
        if path.name.endswith(".zip"):
            continue
        files.append(path)
    return files


def main() -> int:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOADS / ZIP_NAME
    files = iter_files()
    if dest in files:
        files.remove(dest)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/{path.relative_to(ROOT).as_posix()}")
            info.date_time = STAMP
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    with zipfile.ZipFile(dest) as archive:
        members = archive.namelist()
    print(f"PASS: {dest.name} bytes={dest.stat().st_size} sha256={digest} members={len(members)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
