"""Record the Epigen demo video in WebKit (Safari's engine).

Run once from the project root with the app server already up:

    .venv/bin/python video/record_demo.py

Drives http://localhost:8000 with Playwright WebKit at 1920x1080:
open page, upload demo/jacket.png, Ask both, wait for the decision card,
hover a family chip, scroll to the memory map, hover a lit dot, log
"Returned", ask again, wait for the NEW badge, open the Before panel.
Pauses ~2s after each step; waits up to 90s per answer.
Saves video/assets/live_demo.webm. Never touches .env.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(ROOT, ".playwright-browsers"),
)

URL = "http://localhost:8000"
OUT = os.path.join(ROOT, "video", "assets", "live_demo.webm")
PAUSE = 2.0
ANSWER_TIMEOUT = 90000


def step(name: str) -> None:
    print(f"STEP: {name}", flush=True)
    time.sleep(PAUSE)


def main() -> int:
    from playwright.sync_api import sync_playwright

    os.makedirs(os.path.join(ROOT, "video", "assets"), exist_ok=True)
    started = time.perf_counter()
    with sync_playwright() as p:
        try:
            browser = p.webkit.launch(headless=True)
        except Exception as exc:
            print(f"WEBKIT LAUNCH FAILED: {type(exc).__name__}: {exc}")
            return 3
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=os.path.join(ROOT, "video", ".recording"),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        try:
            page.goto(URL, timeout=30000)
            page.wait_for_selector("#ask", timeout=30000)
            step("page loaded")
            page.set_input_files("#photo", os.path.join(ROOT, "demo", "jacket.png"))
            step("photo uploaded")
            page.click("#ask")
            page.wait_for_selector(
                "#decision:not([hidden])", timeout=ANSWER_TIMEOUT
            )
            step("first answer ready (decision card visible)")
            page.hover(".chip.fam >> nth=0", timeout=30000)
            step("hovered a family chip")
            page.locator("#mapPanel").scroll_into_view_if_needed(timeout=30000)
            step("scrolled to the memory map")
            page.hover("circle.dot[stroke] >> nth=0", timeout=30000)
            step("hovered a lit memory dot")
            page.click("#outcome >> text=Returned", timeout=30000)
            step("logged outcome Returned")
            page.click("#ask")
            page.wait_for_selector(".newbadge", timeout=ANSWER_TIMEOUT)
            step("second answer ready (NEW badge visible)")
            page.click("#beforeDetails summary", timeout=30000)
            step("opened the Before panel")
        finally:
            page.close()
            video = page.video
            if video is not None:
                video.save_as(OUT)
            browser.close()
    print(f"saved {OUT} in {time.perf_counter() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
