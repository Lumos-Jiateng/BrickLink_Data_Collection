#!/usr/bin/env python
"""
download_all.py
---------------
Download all (or a slice of) BrickLink Studio models to model_files/.

Usage:
    python download_all.py                  # download everything
    python download_all.py --limit 50       # first 50 models only
    python download_all.py --start 200      # resume from position 200
    python download_all.py --start 200 --limit 100   # positions 200-299
"""

import os, sys, json, time, argparse, re
from pathlib import Path

os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(Path.home() / "Library" / "Caches" / "ms-playwright"),
)

from playwright.sync_api import sync_playwright
from tqdm import tqdm

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
STATE_FILE = BASE_DIR / "bricklink_state.json"
IDS_FILE   = BASE_DIR / "model_id" / "gallery_ids_downloadable.json"
OUT_DIR    = BASE_DIR / "model_files"
OUT_DIR.mkdir(exist_ok=True)

RETRY_LIMIT = 2      # retries per model on timeout
WAIT_SEC    = 0.5    # short pause between models


# ── helpers ────────────────────────────────────────────────────────────────────

def clean_filename(model_id: str, suggested: str) -> str:
    """Return  '<id>_<name_with_underscores>'  e.g. '62_Alien.io'"""
    # Strip leading/trailing whitespace, collapse spaces → _
    name = re.sub(r"\s+", "_", suggested.strip())
    # Remove any remaining double-underscores that may already be in the name
    name = re.sub(r"_+", "_", name)
    # Strip a leading underscore if the suggested name happened to start with one
    name = name.lstrip("_")
    return f"{model_id}_{name}"


def already_downloaded(model_id: str) -> bool:
    """True if a file starting with '<id>_' already exists in OUT_DIR."""
    return any(OUT_DIR.glob(f"{model_id}_*"))


def download_model(page, model_id: str, retries: int = RETRY_LIMIT) -> int | None:
    """
    Download a single model.  Returns file size in bytes, or None on failure.
    Skips silently if the file was already downloaded.
    """
    if already_downloaded(model_id):
        existing = next(OUT_DIR.glob(f"{model_id}_*"))
        return existing.stat().st_size  # count it but skip re-download

    url = f"https://www.bricklink.com/_file/studio/downloadModel?idModel={model_id}"
    #import ipdb; ipdb.set_trace()

    for attempt in range(1, retries + 2):
        try:
            with page.expect_download(timeout=45_000) as dl_info:
                try:
                    page.goto(url, wait_until="domcontentloaded")
                except Exception:
                    pass   # navigation interrupted by download — expected
            dl = dl_info.value
            suggested = dl.suggested_filename or f"model_{model_id}.io"
            fname = clean_filename(model_id, suggested)
            target = OUT_DIR / fname
            dl.save_as(str(target))
            return target.stat().st_size
        except Exception as e:
            if attempt <= retries:
                time.sleep(2)   # brief back-off before retry
            else:
                return None     # give up


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download BrickLink Studio models")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of models to download (default: all)")
    parser.add_argument("--start", type=int, default=0,
                        help="Start index in the ID list (0-based, default: 0)")
    args = parser.parse_args()

    all_ids   = json.loads(IDS_FILE.read_text())
    slice_ids = all_ids[args.start:]
    if args.limit:
        slice_ids = slice_ids[:args.limit]

    total      = len(slice_ids)
    start_idx  = args.start

    print(f"BrickLink model downloader")
    print(f"  IDs file : {IDS_FILE}")
    print(f"  Output   : {OUT_DIR}")
    print(f"  Range    : [{start_idx}, {start_idx + total}) of {len(all_ids):,} total IDs")
    print()

    sizes      = []
    failed     = []
    skipped    = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=str(STATE_FILE),
            accept_downloads=True,
        )
        page = ctx.new_page()

        bar = tqdm(
            slice_ids,
            desc="Downloading",
            unit="model",
            dynamic_ncols=True,
        )

        for mid in bar:
            if already_downloaded(mid):
                skipped += 1
                bar.set_postfix(fail=len(failed), skip=skipped, refresh=False)
                continue

            size = download_model(page, mid)

            if size is None:
                failed.append(mid)
            else:
                sizes.append(size)

            bar.set_postfix(fail=len(failed), skip=skipped, refresh=False)
            time.sleep(WAIT_SEC)

        browser.close()

    # ── final report ──────────────────────────────────────────────────────────
    downloaded = len(sizes)
    total_mb   = sum(sizes) / 1024**2
    avg_mb     = (sum(sizes) / downloaded / 1024**2) if downloaded else 0

    print(f"\n{'─'*60}")
    print(f"  Downloaded : {downloaded:,} models  ({total_mb:.1f} MB)")
    print(f"  Skipped    : {skipped:,}  (already present)")
    print(f"  Failed     : {len(failed):,}")
    print(f"  Avg size   : {avg_mb:.2f} MB / model")

    if downloaded:
        est_total_gb = avg_mb * len(all_ids) / 1024
        print(f"\n  Estimated total for all {len(all_ids):,} models @ avg: {est_total_gb:.1f} GB")

    if failed:
        fail_log = OUT_DIR / "failed_ids.txt"
        fail_log.write_text("\n".join(failed) + "\n")
        print(f"\n  Failed IDs saved to: {fail_log}")

    print(f"{'─'*60}")


if __name__ == "__main__":
    main()
