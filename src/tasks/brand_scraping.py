from typing import Any, Dict, Tuple

from config.constants import LETTER_GROUPS, LETTER_PAGE_MAPPING
from core.base_task import BaseTask
from scraper import setup_browser
from scraper.brand_scraper import BrandScraper
from storage.json_storage import JsonStorage


class BrandScrapingTask(BaseTask):
    """ブランドスクレイピングタスク"""

    def __init__(self, letter_group: int):
        self.letter_group = letter_group
        self.playwright = None
        self.browser = None
        self.scraper = None

    async def setup(self) -> None:
        """タスクのセットアップ"""
        self.playwright, self.browser = await setup_browser()
        self.scraper = BrandScraper(self.browser)

    async def process_letter(self, letter: str) -> Tuple[str, int]:
        """文字ごとの処理"""
        try:
            page_nums = LETTER_PAGE_MAPPING.get(letter, [])
            if not page_nums:
                print(f"No page mapping found for letter {letter}")
                return letter, 0

            brands = await self.scraper.scrape_letter(letter, page_nums)
            if brands:
                JsonStorage.save_brands(brands, letter)
            return letter, len(brands)
        except Exception as e:
            print(f"Error processing letter {letter}: {e}")
            return letter, 0

    async def execute(self, **kwargs: Dict[str, Any]) -> None:
        """タスクの実行"""
        try:
            letters = LETTER_GROUPS[self.letter_group]
            print(f"Processing letter group {self.letter_group}: {letters}")

            for letter in letters:
                result = await self.process_letter(letter)
                print(
                    f"Completed processing letter {result[0]}: found {result[1]} brands")

        except Exception as e:
            print(f"Critical error in brand scraping task: {e}")
            raise

    async def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        if self.scraper:
            await self.scraper.cleanup()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
