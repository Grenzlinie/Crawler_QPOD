# QPOD Download Guide (English)

This repository ships a set of Python tools that help you scrape material IDs from the QPOD website and download the corresponding CIF files in bulk. Below is a quick start guide covering environment setup, dependencies, and the recommended script order.

## Environment

- Python 3.9+ (prefer a virtual environment)
- Dependencies installed via `pip`

### Create & activate a virtual environment (example)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows use .venv\Scripts\activate
```

### Install dependencies

Required packages: `requests`, `beautifulsoup4`, and optional `tqdm` for progress bars.

```bash
pip install requests beautifulsoup4 tqdm
```

If you keep a `requirements.txt`, run `pip install -r requirements.txt`.

> [!WARNING]
> Since QPOD does not provide a download interface for the complete dataset, it is only possible to use a script to obtain all the data. However, this script is for learning and communication purposes only, and the author is not responsible for any issues arising from its use!

## Scripts overview

### 1. Fetch material IDs — `download_cif_list.py`

```bash
python download_cif_list.py
```

- Iterates the QPOD listing for the chosen `sid` and appends results to `qpod_sid<sid>_material_ids.txt`.
- Existing entries are skipped so the script can resume safely.

### 2. Deduplicate IDs — `dedup_ids.py`

```bash
python dedup_ids.py
```

- Reads `qpod_sid73_material_ids.txt`, keeps the first occurrence of each ID, and writes a `.bak` backup before modifying.
- Adjust `IDS_PATH`/`BACKUP_PATH` in the script if you use different filenames.

### 3. Check missing CIFs — `check_cifs.py`

```bash
python check_cifs.py
```

- Compares the ID list with files under `cif_downloads/`, prints missing/extra IDs, and writes them to `missing_ids.txt`.
- Customize `IDS_FILE`, `CIF_DIR`, and `MISSING_FILE` at the top if needed.

### 4. Download CIFs — `download_cifs.py`

```bash
python download_cifs.py \
  --ids missing_ids.txt \
  --out cif_downloads \
  --timeout 30 \
  --log download_status.csv \
  --batch-size 5
```

- `--ids`: path to the ID list (defaults to `missing_ids.txt`).
- `--out`: output directory; created automatically if missing.
- `--timeout`: per-request timeout in seconds.
- `--log`: CSV tracking download results for resumable runs.
- `--batch-size`: parallel download threads (tune for your network).
- When `tqdm` is installed you’ll see a progress bar; otherwise logging falls back to plain prints.

## Tips

- Re-run scripts as needed; the log and missing list help skip already downloaded items.
- Test with a small subset before long sessions to verify network settings.
- For proxies or custom throttling, modify the scripts (e.g., wrap requests in a tailored `Session`).
