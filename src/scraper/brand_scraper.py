# scraper/brand_scraper.py
import asyncio
from typing import List, Optional

from playwright.async_api import Browser, BrowserContext, Page

from models.brand import Brand

from .extractor import extract_brands_data
from .page_handler import get_page_with_retry
from .utils import get_random_delay, normalize_url


class BrandScraper:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def setup_context(self):
        """ブラウザコンテキストの設定"""
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            java_script_enabled=True,
        )

        # JavaScript時計の改ざんを防ぐ
        await self.context.add_init_script("""
            {
                const originalDate = Date;
                const originalNavigator = navigator;
                const originalChrome = window.chrome;
                
                Object.defineProperty(window, 'chrome', {
                    get: function() { return originalChrome; }
                });
                
                Object.defineProperty(window, 'navigator', {
                    get: function() { return originalNavigator; }
                });
                
                window.Date = originalDate;
            }
        """)

        self.page = await self.context.new_page()

    async def cleanup(self):
        """リソースのクリーンアップ"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()

    async def _process_brand_data(self, brand_data: dict, page_num: str) -> Optional[Brand]:
        """ブランドデータの処理"""
        try:
            return Brand(
                name=brand_data['name'],
                url=normalize_url(brand_data['url']),
                perfume_count=brand_data['perfume_count'],
                page_number=page_num
            )
        except Exception as e:
            print(f"Error processing brand data: {e}")
            return None

    async def _extract_brands_from_page(self, letter: str, page_num: str) -> List[Brand]:
        """1ページからブランド情報を抽出"""
        brands = []
        max_retries = 3
        url = f"https://www.fragrantica.com/designers-{page_num}/#{letter}"
        print(f"\naccessing {url}")

        for attempt in range(max_retries):
            try:
                print(
                    f"\nFetching brands starting with '{letter}' from page {page_num} (attempt {attempt + 1})")

                if not await get_page_with_retry(self.page, url):
                    print(
                        f"Failed to load page {page_num} after {max_retries} attempts")
                    continue

                if not await self._verify_page_content(letter):
                    continue

                brands_data = await self._get_brands_data(letter)
                if brands_data:
                    brands = [
                        brand for brand_data in brands_data
                        if (brand := await self._process_brand_data(brand_data, page_num))
                    ]
                    print(
                        f"Successfully collected {len(brands)} brands for letter {letter} on page {page_num}")
                    break
                elif attempt < max_retries - 1:
                    await asyncio.sleep(get_random_delay(5, 10))

            except Exception as e:
                print(
                    f"Error on attempt {attempt + 1} for page {page_num}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(get_random_delay(5, 10))

        return brands

    async def _verify_page_content(self, letter: str) -> bool:
        """ページコンテンツの検証"""
        header = await self.page.wait_for_selector(f"h2[id='{letter}']", timeout=30000)
        if not header:
            print(f"Header for letter {letter} not found")
            return False

        await header.scroll_into_view_if_needed()
        await asyncio.sleep(get_random_delay(1, 2))
        return True

    async def _get_brands_data(self, letter: str) -> List[dict]:
        """ブランドデータの取得"""
        grid_selector = f"h2[id='{letter}']+div.grid-x"
        brands_data = await extract_brands_data(self.page, grid_selector)
        print(f"Found {len(brands_data)} brand elements")
        return brands_data

    async def scrape_letter(self, letter: str, page_nums: List[str]) -> List[Brand]:
        """指定した文字のブランド情報を取得"""
        if not self.page:
            await self.setup_context()

        all_brands = []
        for page_num in page_nums:
            brands = await self._extract_brands_from_page(letter, page_num)
            all_brands.extend(brands)

        # 重複を除去
        unique_brands = {brand.url: brand for brand in all_brands}.values()
        print(
            f"Total unique brands found for letter {letter}: {len(unique_brands)}")
        return list(unique_brands)
