# pip install playwright
# playwright install

from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
import re
import time

STATE_FILE = "bricklink_state.json"
OUT_DIR = Path("bricklink_models")
OUT_DIR.mkdir(exist_ok=True)

# Example gallery/search page(s) to crawl
START_URLS = [
    # Replace with actual gallery pages you want to crawl
    "https://www.bricklink.com/v3/studio/gallery.page",
]

def manual_login_and_save_state():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto("https://www.bricklink.com/", wait_until="domcontentloaded")
        print("Log in manually in the opened browser, then press Enter here...")
        input()
        context.storage_state(path=STATE_FILE)
        browser.close()

def extract_model_ids_from_page(page):
    ids = set()

    # collect links from DOM
    hrefs = page.eval_on_selector_all(
        "a",
        "els => els.map(a => a.href).filter(Boolean)"
    )

    for href in hrefs:
        if "idModel=" in href:
            try:
                qs = parse_qs(urlparse(href).query)
                if "idModel" in qs:
                    ids.add(qs["idModel"][0])
            except Exception:
                pass

    # fallback: regex over page content
    html = page.content()
    for m in re.finditer(r"idModel=(\d+)", html):
        ids.add(m.group(1))

    return ids

def download_model(context, model_id):
    page = context.new_page()
    download_url = f"https://www.bricklink.com/_file/studio/downloadModel?idModel={model_id}"

    try:
        with page.expect_download(timeout=15000) as dl_info:
            page.goto(download_url, wait_until="domcontentloaded")
        download = dl_info.value
        suggested = download.suggested_filename
        target = OUT_DIR / f"{model_id}__{suggested}"
        download.save_as(str(target))
        print(f"Downloaded {model_id} -> {target.name}")
        return True
    except Exception as e:
        print(f"Skipped {model_id}: {e}")
        return False
    finally:
        page.close()

def crawl_and_download():
    if not Path(STATE_FILE).exists():
        raise FileNotFoundError(
            f"{STATE_FILE} not found. Run manual_login_and_save_state() first."
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=STATE_FILE, accept_downloads=True)
        page = context.new_page()

        all_ids = set()

        for url in START_URLS:
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(2)
            all_ids |= extract_model_ids_from_page(page)

            # Optional: paginate / infinite scroll here if needed

        print(f"Found {len(all_ids)} candidate model IDs")

        for model_id in sorted(all_ids):
            download_model(context, model_id)
            time.sleep(1)  # be gentle

        browser.close()

if __name__ == "__main__":
    # First run once:
    #manual_login_and_save_state()

    # Then switch to:
    crawl_and_download()