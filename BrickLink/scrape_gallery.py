"""
scrape_gallery.py
-----------------
Scrapes all downloadable model IDs from the BrickLink Studio Gallery.

Strategy:
  1. Navigate to the "Popular" tab (shows all categories)
  2. Set the "Show" filter to "Downloadable" (value=2)
  3. Keep clicking "Load more creations" until the button disappears
  4. Extract idModel from card links in the DOM after every batch

Two output files are saved after every click so progress survives interruptions:
  gallery_ids_downloadable.json  — sorted list of downloadable model IDs
  gallery_ids_all.json           — sorted list of ALL model IDs seen (no filter)

Run:
    PLAYWRIGHT_BROWSERS_PATH=~/Library/Caches/ms-playwright \
      /path/to/osworld/bin/python scrape_gallery.py
"""

import os, json, re, time
from pathlib import Path

os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(Path.home() / "Library" / "Caches" / "ms-playwright"),
)

from playwright.sync_api import sync_playwright

# ── config ─────────────────────────────────────────────────────────────────────
STATE_FILE    = Path(__file__).parent / "bricklink_state.json"
OUT_DIR       = Path(__file__).parent / "model_id"
OUT_DIR.mkdir(exist_ok=True)
OUT_DL        = OUT_DIR / "gallery_ids_downloadable.json"
OUT_ALL       = OUT_DIR / "gallery_ids_all.json"

GALLERY_URL    = "https://www.bricklink.com/v3/studio/gallery.page"
LOAD_MORE_SEL  = 'button[data-ts-name="studio-gallery-feed__load-more"]'
FILTER_SEL     = 'select[data-ts-name="studio-gallery-results__filter--show"]'
CARD_LINK_SEL  = "a[href*='design.page?idModel=']"

LOAD_WAIT_SEC  = 3   # seconds to wait after each click / filter change

# ── helpers ────────────────────────────────────────────────────────────────────

def ids_from_dom(page) -> set[str]:
    hrefs = page.eval_on_selector_all(
        CARD_LINK_SEL,
        "els => [...new Set(els.map(a => a.href))]",
    )
    result = set()
    for href in hrefs:
        m = re.search(r"idModel=(\d+)", href)
        if m:
            result.add(m.group(1))
    return result


def save(dl_ids: set[str], all_ids: set[str]) -> None:
    OUT_DL.write_text(json.dumps(sorted(dl_ids, key=int), indent=2))
    OUT_ALL.write_text(json.dumps(sorted(all_ids, key=int), indent=2))


# ── main ───────────────────────────────────────────────────────────────────────

def scrape():
    if not STATE_FILE.exists():
        raise FileNotFoundError(f"Missing {STATE_FILE} — log in via test.py first.")

    # Resume from a previous partial run if files already exist in model_id/
    dl_ids:  set[str] = set(json.loads(OUT_DL.read_text())) if OUT_DL.exists() else set()
    all_ids: set[str] = set(json.loads(OUT_ALL.read_text())) if OUT_ALL.exists() else set()
    if dl_ids:
        print(f"Resuming: {len(dl_ids)} downloadable / {len(all_ids)} total already in {OUT_DIR.name}/")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx     = browser.new_context(
            storage_state=str(STATE_FILE),
            accept_downloads=False,
        )
        page = ctx.new_page()

        # ── 1. Load gallery ──────────────────────────────────────────────────
        print("Loading gallery…")
        page.goto(GALLERY_URL, wait_until="networkidle", timeout=60_000)
        time.sleep(3)

        # ── 2. Switch to "Popular" tab (has the Show filter) ─────────────────
        print("Switching to Popular tab…")
        page.click('li[data-ts-name="studio-gallery-tab"][data-ts-id="0"]')
        time.sleep(LOAD_WAIT_SEC)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass

        # Grab all IDs visible so far (unfiltered)
        all_ids |= ids_from_dom(page)
        print(f"  After Popular tab load: {len(all_ids)} total IDs visible")

        # ── 3. Apply "Downloadable" filter ───────────────────────────────────
        print('Setting Show filter to "Downloadable"…')
        filter_el = page.query_selector(FILTER_SEL)
        if not filter_el:
            print("  WARNING: filter select not found — scraping without filter.")
        else:
            filter_el.select_option(value="2")
            time.sleep(LOAD_WAIT_SEC)
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass

        dl_ids |= ids_from_dom(page)
        all_ids |= dl_ids
        save(dl_ids, all_ids)
        print(f"  After filter: {len(dl_ids)} downloadable IDs")

        # ── 4. Click "Load more" until exhausted ─────────────────────────────
        click_n         = 0
        no_new_streak   = 0

        while True:
            btn = page.query_selector(LOAD_MORE_SEL)
            if not btn:
                print(f"No more pages after {click_n} clicks.")
                break

            prev = len(dl_ids)
            try:
                btn.scroll_into_view_if_needed()
                btn.click()
                click_n += 1
                time.sleep(LOAD_WAIT_SEC)
                try:
                    page.wait_for_load_state("networkidle", timeout=15_000)
                except Exception:
                    pass

                new_batch = ids_from_dom(page)
                dl_ids   |= new_batch
                all_ids  |= new_batch
                save(dl_ids, all_ids)

                added = len(dl_ids) - prev
                print(f"  click {click_n:4d}: +{added:4d}  →  downloadable={len(dl_ids)}")

                if added == 0:
                    no_new_streak += 1
                    if no_new_streak >= 3:
                        print("  3 consecutive clicks with no new IDs — stopping.")
                        break
                else:
                    no_new_streak = 0

            except Exception as e:
                print(f"  Error on click {click_n}: {e}")
                break

        browser.close()

    save(dl_ids, all_ids)
    print("=" * 50)
    print(f"Done!  {len(dl_ids)} downloadable IDs,  {len(all_ids)} total seen")
    print(f"  Downloadable  → {OUT_DL}")
    print(f"  All           → {OUT_ALL}")


if __name__ == "__main__":
    scrape()
