#!/usr/bin/env python3
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent  # 视情况调整
IDS_FILE = ROOT / "qpod_sid73_material_ids.txt"
CIF_DIR = ROOT / "cif_downloads"
MISSING_FILE = ROOT / "missing_ids.txt"
CASEFIX_SUFFIX = "__casefix-"

def iter_ids(path: pathlib.Path) -> set[str]:
    ids = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.add(line)
    return ids

def iter_cif_names(directory: pathlib.Path) -> set[str]:
    if not directory.exists():
        return set()
    names: set[str] = set()
    for entry in directory.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".cif":
            stem = entry.stem
            if CASEFIX_SUFFIX in stem:
                stem = stem.split(CASEFIX_SUFFIX, 1)[0]
            names.add(stem)
    return names

def main() -> None:
    expected = iter_ids(IDS_FILE)
    actual = iter_cif_names(CIF_DIR)

    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    print(f"Total IDs listed: {len(expected)}")
    print(f"CIF files found:  {len(actual)}")
    print()

    if missing:
        print("Missing CIFs (IDs with no file):")
        for mid in missing:
            print(f"  - {mid}")
    else:
        print("No missing CIFs.")

    print()

    if extra:
        print("Extra CIF files (not in ID list):")
        for mid in extra:
            print(f"  - {mid}")
    else:
        print("No extra CIF files.")

    MISSING_FILE.write_text("\n".join(missing), encoding="utf-8")
    print(f"\nMissing IDs saved to {MISSING_FILE}")

if __name__ == "__main__":
    main()
