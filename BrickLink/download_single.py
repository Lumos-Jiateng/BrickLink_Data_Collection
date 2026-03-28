import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Point Playwright at the real browser cache (overrides any sandbox redirect)
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(Path.home() / "Library" / "Caches" / "ms-playwright"),
)

STATE_FILE = Path(__file__).parent / "bricklink_state.json"
OUT_DIR    = Path(__file__).parent          # save right here in BrickLink/
MODEL_ID   = "799517"

def download_single(model_id: str) -> None:
    if not STATE_FILE.exists():
        raise FileNotFoundError(
            f"State file not found: {STATE_FILE}\n"
            "Run manual_login_and_save_state() in test.py first."
        )

    download_url = f"https://www.bricklink.com/_file/studio/downloadModel?idModel={model_id}"
    print(f"Downloading model {model_id} from:\n  {download_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=str(STATE_FILE),
            accept_downloads=True,
        )
        page = context.new_page()

        try:
            with page.expect_download(timeout=30_000) as dl_info:
                try:
                    page.goto(download_url, wait_until="domcontentloaded")
                except Exception:
                    pass  # navigation is interrupted by the download starting — expected
            download = dl_info.value
            suggested = download.suggested_filename or f"model_{model_id}.io"
            target = OUT_DIR / f"{model_id}__{suggested}"
            download.save_as(str(target))
            print(f"Success! Saved to: {target}")
        except Exception as e:
            print(f"Download failed: {e}")
        finally:
            page.close()
            browser.close()


if __name__ == "__main__":
    download_single(MODEL_ID)
