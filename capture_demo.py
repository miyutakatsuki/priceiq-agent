"""Capture Streamlit demo screenshots for embedding in Phase3_Slides.pptx.

Run: python3 capture_demo.py
Outputs: assets/demo_*.png
"""
import asyncio
import pathlib
from playwright.async_api import async_playwright

OUT = pathlib.Path("assets")
OUT.mkdir(exist_ok=True)

URL = "http://localhost:8501"
VIEWPORT = {"width": 1600, "height": 1000}  # 16:10 high-res


async def capture():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,  # retina
        )
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_selector("text=PriceIQ", timeout=10000)
        await page.wait_for_timeout(1500)

        # 1) Cached demo top: hero + tabs + sample picker + query header
        await page.screenshot(path=str(OUT / "demo_top.png"), full_page=False)
        print(f"✅ {OUT/'demo_top.png'}")

        # 2) Scroll down to recommendation cards
        await page.evaluate("window.scrollBy(0, 460)")
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT / "demo_cards.png"), full_page=False)
        print(f"✅ {OUT/'demo_cards.png'}")

        # 3) Scroll further to revenue chart + caveat + timeline
        await page.evaluate("window.scrollBy(0, 460)")
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT / "demo_chart.png"), full_page=False)
        print(f"✅ {OUT/'demo_chart.png'}")

        # 4) Click Live agent tab — try by role/name
        try:
            await page.get_by_role("tab", name="Live agent").click()
            await page.wait_for_timeout(800)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(300)
            await page.screenshot(path=str(OUT / "demo_live.png"), full_page=False)
            print(f"✅ {OUT/'demo_live.png'}")
        except Exception as e:
            print(f"⚠️  Live tab not captured: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(capture())
