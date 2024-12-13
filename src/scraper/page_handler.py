import asyncio

from playwright.async_api import Page

from .cloudflare import verify_cloudflare_passed
from .utils import get_random_delay


async def get_page_with_retry(page: Page, url: str, max_retries: int = 3) -> bool:
    """ページの読み込みを試行（改善版）"""
    for attempt in range(max_retries):
        try:
            print(f"Loading page attempt {attempt + 1}")

            # より緩やかな条件でページを読み込み
            await page.goto(url,
                            wait_until='domcontentloaded',
                            timeout=60000)

            # ページが完全に読み込まれるまで待機
            try:
                await page.wait_for_load_state('load', timeout=30000)
            except Exception as e:
                print(f"Load state timeout, but continuing: {e}")

            # スクロールしてコンテンツを読み込み
            await page.evaluate("""
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)
            await asyncio.sleep(2)

            await page.evaluate("window.scrollTo(0, 0);")
            await asyncio.sleep(1)

            # Cloudflareチェックの通過を待機
            if await verify_cloudflare_passed(page):
                return True

            print(f"Failed to verify page content on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                await asyncio.sleep(get_random_delay(8, 15))

        except Exception as e:
            print(f"Error loading page on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(get_random_delay(8, 15))

    return False
