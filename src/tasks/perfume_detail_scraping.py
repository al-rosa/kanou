import asyncio
import json
import logging
import random
import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.base_task import BaseTask
from models.perfume import Accord, Perfume, Season, TimeOfDay
from scraper import setup_browser
from scraper.brand_scraper import BrandScraper
from scraper.cloudflare_handler import CloudflareHandler
from scraper.retry_decorator import with_retry
from scraper.utils import get_random_delay


class PerfumeDetailScrapingTask(BaseTask):
    """香水詳細情報スクレイピングタスク"""

    def __init__(
        self,
        brand_data_dir: str = 'data',
        delay_min: float = 2.0,
        delay_max: float = 4.0,
        max_retries: int = 3
    ):
        self.brand_data_dir = Path(brand_data_dir)
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.playwright = None
        self.browser = None
        self.scraper = None
        self.context = None
        self.page = None
        self.cloudflare_handler = None
        self.logger = logging.getLogger(__name__)

    async def setup(self) -> None:
        """タスクのセットアップ"""
        self.logger.info("Setting up PerfumeDetailScrapingTask")
        self.playwright, self.browser = await setup_browser()
        self.scraper = BrandScraper(self.browser)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.cloudflare_handler = CloudflareHandler(self.page)

    async def execute(self, **kwargs: Dict[str, Any]) -> None:
        """タスクの実行"""
        try:
            self.logger.info("Starting perfume detail scraping")
            brands = await self.load_brand_files()

            for brand in brands:
                try:
                    self.logger.info(f"Processing brand: {brand['name']}")
                    perfume_urls = await self.extract_perfume_urls(brand['url'])

                    for perfume_url in perfume_urls:
                        try:
                            self.logger.info(
                                f"Processing perfume: {perfume_url}")
                            detail_data = await self.extract_perfume_data(perfume_url)

                            # 香水名はURLから抽出
                            perfume_name = perfume_url.split(
                                '/')[-1].replace('.html', '')

                            perfume = Perfume(
                                name=perfume_name,
                                brand=brand['name'],
                                target_gender=detail_data['target_gender'],
                                main_accords=[
                                    Accord(**accord) for accord in detail_data['main_accords']
                                ],
                                seasons=Season(**detail_data['seasons']),
                                time_of_day=TimeOfDay(
                                    **detail_data['time_of_day'])
                            )

                            await self.save_perfume_data(perfume, brand['name'])
                            await asyncio.sleep(
                                get_random_delay(
                                    self.delay_min, self.delay_max)
                            )

                        except Exception as e:
                            self.logger.error(
                                f"Error processing perfume {perfume_url}: {e}",
                                exc_info=True
                            )
                            continue

                except Exception as e:
                    self.logger.error(
                        f"Error processing brand {brand['name']}: {e}",
                        exc_info=True
                    )
                    continue

        except Exception as e:
            self.logger.error(
                f"Critical error in perfume detail scraping: {e}",
                exc_info=True
            )
            raise

    async def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        self.logger.info("Cleaning up resources")
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.scraper:
            await self.scraper.cleanup()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def load_brand_files(self) -> List[Dict]:
        """ブランドデータファイルの読み込み"""
        all_brands = []
        for file_path in self.brand_data_dir.glob('fragrantica_brands_*.json'):
            self.logger.info(f"Loading brand file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                brands = json.load(f)
                all_brands.extend(brands)
        return all_brands

    @with_retry(max_retries=5,
                initial_delay=5.0,
                max_delay=30.0
                )
    async def extract_perfume_urls(self, brand_url: str) -> List[str]:
        """ブランドページから香水の詳細ページURLを抽出"""
        try:
            self.logger.info(f"Extracting perfume URLs from {brand_url}")
            await self.page.goto(brand_url, wait_until='domcontentloaded', timeout=60000)

            if not await self.cloudflare_handler.wait_for_challenge_completion():
                raise Exception("Failed to pass Cloudflare challenge")

            try:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            except Exception as e:
                self.logger.warning(f"Network idle timeout: {e}")

            await asyncio.sleep(get_random_delay(self.delay_min, self.delay_max))

            perfume_links = []
            perfume_boxes = await self.page.query_selector_all(
                '.cell.text-left.prefumeHbox'
            )

            for box in perfume_boxes:
                try:
                    link = await box.query_selector('h3 > a')
                    if link:
                        href = await link.get_attribute('href')
                        if href and href.startswith('/perfume/'):
                            full_url = f"https://www.fragrantica.com{href}"
                            name = await link.inner_text()
                            self.logger.info(
                                f"Found perfume: {name.strip()} - {full_url}"
                            )
                            perfume_links.append(full_url)
                except Exception as e:
                    self.logger.error(f"Error extracting perfume URL: {e}")
                    continue

            self.logger.info(f"Found {len(perfume_links)} perfume URLs")
            return perfume_links

        except Exception as e:
            self.logger.error(
                f"Error extracting perfume URLs from brand page: {e}")
            raise

    @with_retry(max_retries=5, initial_delay=5.0, max_delay=30.0)
    async def extract_perfume_data(self, url: str) -> Dict:
        """香水詳細ページからデータを抽出"""
        try:
            self.logger.info(f"Extracting data from {url}")
            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # Cloudflareチェックを試みるが、失敗してもコンテンツの取得を試みる
            await self.cloudflare_handler.wait_for_challenge_completion(timeout=30000)

            # ページの読み込みを確実にする
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(get_random_delay(self.delay_min, self.delay_max))

            # 性別情報の抽出
            target_gender = []
            gender_info = await self.page.evaluate('''
                () => {
                    const h1 = document.querySelector('h1');
                    return h1 ? h1.innerText : null;
                }
            ''')

            if not gender_info:
                self.logger.warning("No content found, might be blocked")
                raise Exception("Failed to extract content")

            if gender_info:
                self.logger.info(f"Found gender info: {gender_info}")
                if 'for women' in gender_info.lower():
                    target_gender.append('women')
                if 'for men' in gender_info.lower():
                    target_gender.append('men')

            # メインアコードの抽出
            accord_bars = await self.page.evaluate('''
                () => {
                    const bars = Array.from(document.getElementsByClassName('accord-bar'));
                    return bars.map(bar => ({
                        text: bar.innerText,
                        style: bar.getAttribute('style')
                    }));
                }
            ''')

            accords = []
            for bar in accord_bars:
                try:
                    name = bar['text'].strip()
                    style = bar['style']
                    if style:
                        width_match = re.search(r'width:\s*([\d.]+)%', style)
                        if width_match:
                            strength = int(float(width_match.group(1)))
                            accords.append({
                                'name': name,
                                'strength': strength
                            })
                            self.logger.info(
                                f"Added accord: {name} ({strength}%)")
                except Exception as e:
                    self.logger.error(f"Error processing accord bar: {e}")
                    continue

            # シーズン情報を探す
            seasons_data = await self.page.evaluate('''
                () => {
                    const seasonElements = Array.from(
                        document.getElementsByClassName('vote-season')
                    );
                    return seasonElements.map(el => ({
                        season: el.getAttribute('data-season'),
                        votes: parseInt(el.innerText)
                    }));
                }
            ''')

            seasons = {
                'spring': False,
                'summer': False,
                'fall': False,
                'winter': False
            }

            for season_data in seasons_data:
                if season_data.get('season') in seasons:
                    seasons[season_data['season']] = season_data.get(
                        'votes', 0) > 50

            # 時間帯情報を探す
            time_of_day_data = await self.page.evaluate('''
                () => {
                    const elements = Array.from(
                        document.querySelectorAll('.vote-time-of-day')
                    );
                    return elements.map(el => ({
                        time: el.getAttribute('data-time'),
                        votes: parseInt(el.innerText)
                    }));
                }
            ''')

            time_of_day = {
                'day': False,
                'night': False
            }

            for tod_data in time_of_day_data:
                if tod_data.get('time') in time_of_day:
                    time_of_day[tod_data['time']] = tod_data.get(
                        'votes', 0) > 50

            # 結果をまとめる
            result = {
                'target_gender': list(set(target_gender)),
                'main_accords': accords,
                'seasons': seasons,
                'time_of_day': time_of_day
            }

            self.logger.info("Successfully extracted perfume data")
            self.logger.debug(f"Extracted data: {result}")

            return result

        except Exception as e:
            self.logger.error(f"Error extracting perfume data: {e}")
            traceback.print_exc()
            raise

    async def save_perfume_data(self, perfume: Perfume, brand_name: str) -> None:
        """香水データの保存"""
        output_dir = self.brand_data_dir / brand_name
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / f"{perfume.name}.json"
        self.logger.info(f"Saving perfume data to {file_path}")

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(perfume.to_dict(), f, ensure_ascii=False, indent=2)

    async def _get_text(self, selector: str) -> str:
        """指定されたセレクターのテキストを取得"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if element:
                return await element.inner_text()
        except Exception:
            pass
        return ""

    async def _get_vote_count(self, vote_type: str) -> int:
        """投票数を取得"""
        try:
            selector = f'.vote-{vote_type}'
            element = await self.page.wait_for_selector(selector, timeout=3000)
            if element:
                text = await element.inner_text()
                return int(text.strip('%'))
        except Exception:
            return 0
