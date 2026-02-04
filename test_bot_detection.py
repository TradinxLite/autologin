
import asyncio
import logging
from autologin.workers.playwright_driver import PlaywrightDriver

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_bot_detection():
    print("Starting bot detection test...")
    async with PlaywrightDriver(headless=False) as driver:
        # Create context
        context = await driver.new_context()
        page = await context.new_page()
        
        # Test 1: Sannysoft Bot Test
        print("Navigating to https://bot.sannysoft.com/ ...")
        await page.goto("https://bot.sannysoft.com/")
        await asyncio.sleep(5)
        
        # Take screenshot
        await page.screenshot(path="bot_test_sannysoft.png", full_page=True)
        
        # Test 2: Dhan Web Page (to see if it blocks WAF)
        print("Navigating to Dhan Web...")
        try:
            await page.goto("https://web.dhan.co/login", timeout=30000)
            await asyncio.sleep(5)
            await page.screenshot(path="bot_test_dhan.png")
            content = await page.content()
            if "Access Denied" in content or "Security" in content:
                print("POSSIBLE BLOCK DETECTED on Dhan")
            else:
                print("Dhan page loaded (check screenshot)")
        except Exception as e:
            print(f"Error loading Dhan: {e}")

        # Keep open for a bit to observe if running interactively
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_bot_detection())
