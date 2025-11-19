#!/usr/bin/env python3
"""Download CIF files for material IDs listed in a text file."""
from __future__ import annotations

import argparse
import csv
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Callable

try:  # Optional progress bar
    from tqdm import tqdm
except ImportError:  # pragma: no cover - fallback if tqdm not installed
    tqdm = None

BASE_URL = "https://qpod.fysik.dtu.dk/material/{id}/download/cif"
DEFAULT_IDS_FILE = pathlib.Path(__file__).with_name("missing_ids.txt")
DEFAULT_OUTPUT_DIR = pathlib.Path(__file__).with_name("cif_downloads")
DEFAULT_LOG_PATH = pathlib.Path(__file__).with_name("download_status.csv")

def load_log(log_path: pathlib.Path) -> list[dict[str, str]]:
    """Return rows already present in log; rows keep original order."""
    if not log_path.exists():
        return []
    try:
        with log_path.open("r", newline="", encoding="utf-8") as handle:
            return [row for row in csv.DictReader(handle)]
    except OSError as exc:
        print(f"[warn] Unable to read existing log {log_path}: {exc}")
        return []

def write_log(log_path: pathlib.Path, rows: list[dict[str, str]]) -> None:
    """Write rows back to the CSV log (overwrite)."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "downloaded"])
            writer.writeheader()
            writer.writerows(rows)
    except OSError as exc:
        print(f"[warn] Unable to write log file {log_path}: {exc}")

def iter_material_ids(ids_path: pathlib.Path) -> list[str]:
    """Return material IDs read from a text file, ignoring blanks and comments."""
    material_ids: list[str] = []
    try:
        with ids_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                material_id = raw_line.strip()
                if not material_id or material_id.startswith("#"):
                    continue
                material_ids.append(material_id)
    except OSError as exc:
        raise SystemExit(f"Failed to read IDs file {ids_path}: {exc}") from exc
    if not material_ids:
        raise SystemExit(f"No material IDs found in {ids_path}.")
    return material_ids

def download_cif(
    material_id: str,
    output_dir: pathlib.Path,
    timeout: float,
    writer: Callable[[str], None],
) -> bool:
    """Download a single CIF file; return True on success."""
    url = BASE_URL.format(id=material_id)

    def resolve_output_path() -> tuple[pathlib.Path, bool]:
        """Return a path to write. If exact-case file exists, mark skip."""
        target_name = f"{material_id}.cif"
        target_lower = target_name.lower()
        output_dir.mkdir(parents=True, exist_ok=True)
        case_collision = False
        if output_dir.exists():
            for entry in output_dir.iterdir():
                if not entry.is_file():
                    continue
                if entry.name.lower() != target_lower:
                    continue
                if entry.name == target_name:
                    return entry, True  # exact-case exists
                # same spelling but different case: pick a disambiguated name
                case_collision = True
                break
        if not case_collision:
            return output_dir / target_name, False
        suffix = hashlib.sha1(material_id.encode("utf-8")).hexdigest()[:8]
        return output_dir / f"{material_id}__casefix-{suffix}.cif", False

    output_path, already_exists = resolve_output_path()
    if already_exists and output_path.exists():
        writer(f"[skip] {material_id}: already exists at {output_path}")
        return True
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                writer(f"[fail] {material_id}: HTTP {response.status}")
                return False
            data = response.read()
    except urllib.error.HTTPError as exc:
        writer(f"[fail] {material_id}: HTTP {exc.code} {exc.reason}")
        return False
    except urllib.error.URLError as exc:
        writer(f"[fail] {material_id}: network error {exc.reason}")
        return False
    except TimeoutError:
        writer(f"[fail] {material_id}: request timed out")
        return False
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
    except OSError as exc:
        writer(f"[fail] {material_id}: unable to write file ({exc})")
        return False
    writer(f"[ok] {material_id}: saved to {output_path}")
    return True

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ids",
        type=pathlib.Path,
        default=DEFAULT_IDS_FILE,
        help="Path to the text file containing material IDs (one per line).",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where downloaded CIF files will be stored.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds for each download request.",
    )
    parser.add_argument(
        "--log",
        type=pathlib.Path,
        default=DEFAULT_LOG_PATH,
        help="CSV file that will be updated with download results.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of CIFs to download in parallel (default: 5).",
    )
    return parser.parse_args(argv)

def make_thread_safe_writer(base_writer: Callable[[str], None]) -> Callable[[str], None]:
    """Wrap a writer so messages from multiple threads don't interleave."""
    lock = Lock()
    def safe_writer(message: str) -> None:
        with lock:
            base_writer(message)
    return safe_writer

def main(argv: list[str]) -> int:
    args = parse_args(argv)
    material_ids = iter_material_ids(args.ids)
    log_rows: list[dict[str, str]] = load_log(args.log) if args.log else []
    # Build quick index for updates; keeps earliest occurrence to preserve ordering.
    index: dict[str, int] = {}
    for i, row in enumerate(log_rows):
        material_id = str(row.get("id", "")).strip()
        if material_id and material_id not in index:
            index[material_id] = i
    previously_downloaded = {
        mid for mid, idx in index.items()
        if str(log_rows[idx].get("downloaded", "")).strip().lower() in {"true", "1", "yes", "y"}
    }
    ids_to_process = [mid for mid in material_ids if mid not in previously_downloaded]
    if not ids_to_process:
        print("All listed materials are already downloaded according to the log.")
        return 0

    downloaded = 0
    if tqdm:
        pbar = tqdm(total=len(ids_to_process), desc="Downloading", unit="file")
        base_writer = pbar.write
        def bump():
            pbar.update(1)
    else:
        pbar = None
        base_writer = print
        def bump():
            return None
    writer = make_thread_safe_writer(base_writer)

    max_workers = max(1, args.batch_size)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {
            executor.submit(download_cif, material_id, args.out, args.timeout, writer): material_id
            for material_id in ids_to_process
        }
        for future in as_completed(future_to_id):
            material_id = future_to_id[future]
            try:
                success = future.result()
            except Exception as exc:  # pragma: no cover - unexpected error
                writer(f"[fail] {material_id}: unexpected error {exc}")
                success = False
            if success:
                downloaded += 1
                previously_downloaded.add(material_id)
            if args.log:
                row = {"id": material_id, "downloaded": str(success)}
                if material_id in index:
                    log_rows[index[material_id]] = row  # overwrite previous entry
                else:
                    index[material_id] = len(log_rows)
                    log_rows.append(row)
                write_log(args.log, log_rows)  # persist incrementally so CSV exists even if interrupted
            bump()
            if pbar is None:
                delay = random.uniform(0.5, 1.0)
                time.sleep(delay)
    if args.log:
        write_log(args.log, log_rows)
    print(f"Completed: {downloaded}/{len(material_ids)} downloads succeeded.")
    return 0 if downloaded else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
