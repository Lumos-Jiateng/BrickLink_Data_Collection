"""
download_batch.py
-----------------
Downloads the first N models from gallery_ids_downloadable.json,
saves them to model_files/, then prints a size estimate for the full set.
"""

import os, json, time
from pathlib import Path

os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(Path.home() / "Library" / "Caches" / "ms-playwright"),
)

from playwright.sync_api import sync_playwright

STATE_FILE = Path(__file__).parent / "bricklink_state.json"
IDS_FILE   = Path(__file__).parent / "model_id" / "gallery_ids_downloadable.json"
OUT_DIR    = Path(__file__).parent / "model_files"
OUT_DIR.mkdir(exist_ok=True)

N = 10   # number of models to download for the estimate


def download_model(page, model_id: str) -> Path | None:
    url = f"https://www.bricklink.com/_file/studio/downloadModel?idModel={model_id}"
    try:
        with page.expect_download(timeout=30_000) as dl_info:
            try:
                page.goto(url, wait_until="domcontentloaded")
            except Exception:
                pass   # navigation interrupted by download — expected
        dl = dl_info.value
        name = dl.suggested_filename or f"model_{model_id}.io"
        target = OUT_DIR / f"{model_id}__{name}"
        dl.save_as(str(target))
        return target
    except Exception as e:
        print(f"  [{model_id}] FAILED: {e}")
        return None


def main():
    ids = json.loads(IDS_FILE.read_text())
    total_ids = len(ids)
    sample = ids[:N]

    print(f"Downloading first {N} of {total_ids:,} downloadable models → {OUT_DIR}\n")

    sizes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=str(STATE_FILE),
            accept_downloads=True,
        )
        page = ctx.new_page()

        for i, mid in enumerate(sample, 1):
            target = download_model(page, mid)
            if target:
                size = target.stat().st_size
                sizes.append(size)
                print(f"  [{i:2d}/{N}] {mid:>8}  {size/1024/1024:6.2f} MB  → {target.name}")
            time.sleep(1)

        browser.close()

    # ── Size estimate ──────────────────────────────────────────────────────────
    if not sizes:
        print("No files downloaded — cannot estimate.")
        return

    avg_bytes = sum(sizes) / len(sizes)
    min_bytes = min(sizes)
    max_bytes = max(sizes)

    print(f"""
── Size summary for {len(sizes)} sampled files ──────────────────────────
  Min : {min_bytes/1024/1024:.2f} MB
  Max : {max_bytes/1024/1024:.2f} MB
  Avg : {avg_bytes/1024/1024:.2f} MB
  Total sampled: {sum(sizes)/1024/1024:.1f} MB

── Projection for all {total_ids:,} downloadable models ─────────────────
  @ avg  : {avg_bytes*total_ids/1024**3:.1f} GB
  @ min  : {min_bytes*total_ids/1024**3:.1f} GB  (lower bound)
  @ max  : {max_bytes*total_ids/1024**3:.1f} GB  (upper bound)

── 50 GB budget ─────────────────────────────────────────────────────────
  Models that fit @ avg size : {int(50*1024**3 / avg_bytes):,}
  Models that fit @ max size : {int(50*1024**3 / max_bytes):,}
""")


if __name__ == "__main__":
    main()
