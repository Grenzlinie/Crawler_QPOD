#!/usr/bin/env python3
"""Deduplicate IDs in qpod_sid73_material_ids.txt while preserving order."""
from __future__ import annotations

import pathlib

IDS_PATH = pathlib.Path(__file__).with_name("qpod_sid73_material_ids.txt")
BACKUP_PATH = IDS_PATH.with_suffix(".bak")


def main() -> None:
    text = IDS_PATH.read_text(encoding="utf-8").splitlines()

    # Keep the first occurrence and preserve original order.
    seen: set[str] = set()
    deduped: list[str] = []

    for line in text:
        if not line.strip():
            continue
        if line.startswith("#"):
            deduped.append(line)
            continue
        if line not in seen:
            seen.add(line)
            deduped.append(line)

    if deduped == text:
        print("No duplicates found; file left unchanged.")
        return

    BACKUP_PATH.write_text("\n".join(text) + "\n", encoding="utf-8")
    IDS_PATH.write_text("\n".join(deduped) + "\n", encoding="utf-8")

    print(f"Backup written to {BACKUP_PATH}")
    print(f"Original lines: {len(text)}, unique lines: {len(deduped)}")


if __name__ == "__main__":
    main()
