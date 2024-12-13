import asyncio
import json
import logging
import time
import traceback
from pathlib import Path
from typing import Dict, List, Set

from fake_useragent import UserAgent

from core.base_task import BaseTask
from models.fragrance_basic import FragranceBasicInfo
from scraper import setup_browser
from scraper.brand_scraper import BrandScraper
from scraper.proxy_handler import TorProxyHandler
from scraper.utils import get_random_delay
from utils.logger import setup_logger


class FragranceBasicScrapingTask(BaseTask):

    def __init__(
        self,
        brand_data_dir: str = 'data',
        output_dir: str = 'data/fragrance_basic_info',
        delay_min: float = 1.0,
        delay_max: float = 2.0,
        max_retries: int = 3,
        letter: str = None,
        batch_size: int = 50
    ):
        self.brand_data_dir = Path(brand_data_dir)
        self.output_dir = Path(output_dir)
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.letter = letter
        self.playwright = None
        self.logger = setup_logger()
        self.batch_size = batch_size
        self.last_refresh_time = None
        self.refresh_interval = 300  # 5分ごとにリフレッシュ
        self.brands_since_refresh = 0
        self.max_brands_before_refresh = 40
        self.proxy_handler = TorProxyHandler()
        self.consecutive_429 = 0

    async def should_refresh(self) -> bool:
        """ブラウザをリフレッシュすべきか判断"""
        current_time = time.time()

        # 初回実行時
        if self.last_refresh_time is None:
            self.last_refresh_time = current_time
            return False

        # 時間経過によるリフレッシュ
        time_elapsed = current_time - self.last_refresh_time
        if time_elapsed > self.refresh_interval:
            self.logger.info(
                f"Refreshing due to time elapsed: {time_elapsed:.1f} seconds")
            return True

        # ブランド数によるリフレッシュ
        if self.brands_since_refresh >= self.max_brands_before_refresh:
            self.logger.info(
                f"Refreshing after processing {self.brands_since_refresh} brands")
            return True

        return False

    async def setup(self) -> None:
        """タスクのセットアップ"""
        self.logger.info("Setting up FragranceBasicScrapingTask")
        self.playwright, self.browser, self.context = await setup_browser()

    async def _extract_perfume_urls(self, brand_url: str, max_retries: int = 5) -> List[Dict]:
        """ブランドページから香水の基本情報を抽出"""
        last_error = None
        ua = UserAgent()

        for attempt in range(max_retries):
            page = None
            try:
                self.logger.info(
                    f"Extracting perfume URLs from {brand_url} (attempt {attempt + 1}/{max_retries})")

                page = await self.context.new_page()

                # User-Agentをリクエストごとに変更
                await page.set_extra_http_headers({
                    'User-Agent': ua.random,
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                })

                # リトライ時は初期待機時間を長めに
                if attempt > 0:
                    initial_wait = get_random_delay(20, 30)
                    self.logger.info(
                        f"Initial wait after previous error: {initial_wait:.1f} seconds")
                    await asyncio.sleep(initial_wait)

                # ページ読み込み
                response = await page.goto(
                    brand_url,
                    wait_until='domcontentloaded',
                    timeout=30000 * (attempt + 1)
                )

                if not response:
                    raise Exception("No response received")

                if response.status == 429:
                    # 429エラー時は指数的に増加する待機時間
                    wait_time = get_random_delay(30, 60) * (2 ** attempt)
                    self.logger.warning(
                        f"Rate limit (429) hit on attempt {attempt + 1}, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
                    continue

                if response.status == 403:
                    wait_time = get_random_delay(30, 60) * (attempt + 1)
                    self.logger.warning(
                        f"Received 403 status on attempt {attempt + 1}, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
                    continue

                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                # ランダムなスクロール動作を追加
                await page.evaluate("""
                    window.scrollTo({
                        top: Math.random() * document.body.scrollHeight,
                        behavior: 'smooth'
                    });
                """)

                await asyncio.sleep(get_random_delay(1, 3))

                # コンテンツの存在を確認
                content = await page.content()
                if "Access Denied" in content or "Security Challenge" in content:
                    wait_time = get_random_delay(15, 30) * (attempt + 1)
                    self.logger.warning(
                        f"Access denied or security challenge detected, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
                    continue

                # 香水情報の抽出
                perfumes = await page.evaluate('''
                    () => {
                        const boxes = document.querySelectorAll('.cell.text-left.prefumeHbox');
                        return Array.from(boxes).map(box => {
                            const link = box.querySelector('h3 > a');
                            if (!link) return null;

                            return {
                                name: link.textContent.trim(),
                                url: link.href
                            };
                        }).filter(item => item !== null);
                    }
                ''')

                if not perfumes:
                    self.logger.warning("No perfumes found on the page")
                    await asyncio.sleep(get_random_delay(3, 7))
                    continue

                # URLの正規化と検証
                normalized_perfumes = []
                for perfume in perfumes:
                    try:
                        url = perfume['url']
                        if not url.startswith('http'):
                            url = f"https://www.fragrantica.com{url}"

                        if '/perfume/' not in url:
                            continue

                        normalized_perfumes.append({
                            'name': perfume['name'],
                            'url': url
                        })
                    except Exception as e:
                        self.logger.error(
                            f"Error normalizing perfume URL: {e}")
                        continue

                if normalized_perfumes:
                    self.logger.info(
                        f"Successfully extracted {len(normalized_perfumes)} perfumes")
                    return normalized_perfumes

            except Exception as e:
                last_error = e
                self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")

                # エラーの種類に応じて待機時間を調整
                if '429' in str(e):
                    wait_time = get_random_delay(30, 60) * (2 ** attempt)
                else:
                    wait_time = get_random_delay(10, 20) * (attempt + 1)

                self.logger.info(
                    f"Waiting {wait_time:.1f} seconds before retry")
                await asyncio.sleep(wait_time)

            finally:
                if page:
                    try:
                        await page.close()
                        self.logger.debug("Page closed")
                    except Exception as e:
                        self.logger.error(f"Error closing page: {e}")

        if last_error:
            # 全試行失敗後は特に長い待機を設定
            if '429' in str(last_error):
                wait_time = get_random_delay(120, 180)  # 2-3分の待機
                self.logger.warning(
                    f"Rate limit issues detected, triggering long cool-down: {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)

            self.logger.error(
                f"All attempts failed for {brand_url}: {str(last_error)}")
        return []

    async def save_fragrance_data(self, fragrance: FragranceBasicInfo) -> None:
        """香水基本データの保存"""
        try:
            initial = fragrance.brand_name[0].upper()

            # スラッシュを含む名前を処理
            safe_perfume_name = fragrance.perfume_name.replace('/', '_')

            output_dir = self.output_dir / initial / fragrance.brand_name
            output_dir.mkdir(parents=True, exist_ok=True)

            file_path = output_dir / f"{safe_perfume_name}.json"
            self.logger.info(f"Saving fragrance data to {file_path}")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fragrance.to_dict(), f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving fragrance data: {e}")
            raise

    async def check_brand_completion(self, brand: Dict) -> bool:
        """ブランドの処理が完了しているかチェック"""
        try:
            initial = brand['name'][0].upper()
            brand_dir = self.output_dir / initial / brand['name']

            # ディレクトリが存在しない場合は未完了
            if not brand_dir.exists():
                return False

            # ファイル数をカウント
            file_count = len(list(brand_dir.glob('*.json')))

            # perfume_countと比較
            if file_count >= int(brand['perfume_count']):
                self.logger.info(
                    f"Brand {brand['name']} already processed ({file_count}/{brand['perfume_count']} perfumes)")
                return True

            self.logger.info(
                f"Brand {brand['name']} partially processed ({file_count}/{brand['perfume_count']} perfumes)")
            return False

        except Exception as e:
            self.logger.error(f"Error checking brand completion: {e}")
            return False

    async def deep_refresh(self):
        """完全なブラウザリフレッシュ"""
        self.logger.info("Performing deep refresh of browser and context")
        try:
            # 既存のリソースをクリーンアップ
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()

            # 新しいブラウザセッションを作成
            self.logger.info("Creating new browser session...")
            _, self.browser, self.context = await setup_browser()

            # より長い待機時間を設定
            await asyncio.sleep(get_random_delay(20, 30))

            self.logger.info("Deep refresh completed")
            return True
        except Exception as e:
            self.logger.error(f"Error during deep refresh: {e}")
            return False

    async def execute(self) -> None:
        try:
            brands = await self.load_brand_files()
            self.logger.info(f"Loaded {len(brands)} brands to process")
            self.last_refresh_time = time.time()
            self.brands_since_refresh = 0
            consecutive_errors = 0  # エラー発生の連続カウント

            # バッチ処理を実装
            for i in range(0, len(brands), self.batch_size):
                batch = brands[i:i + self.batch_size]
                self.logger.info(
                    f"Processing batch {i//self.batch_size + 1}, brands {i+1} to {min(i+self.batch_size, len(brands))}")

                for brand in batch:
                    try:
                        # 処理済みのブランドはスキップ
                        if await self.check_brand_completion(brand):
                            continue

                        self.logger.info(f"Processing brand: {brand['name']}")
                        perfumes = await self._extract_perfume_urls(brand['url'])

                        if perfumes:
                            consecutive_errors = 0  # 成功したらリセット
                            for perfume in perfumes:
                                try:
                                    fragrance = FragranceBasicInfo(
                                        brand_name=brand['name'],
                                        perfume_name=perfume['name'],
                                        url=perfume['url']
                                    )
                                    await self.save_fragrance_data(fragrance)
                                    await asyncio.sleep(0.5)

                                except Exception as e:
                                    self.logger.error(
                                        f"Error saving perfume data: {e}")
                                    continue
                        else:
                            consecutive_errors += 1
                            if consecutive_errors >= 3:  # 3回連続でエラーが発生した場合
                                self.logger.warning(
                                    f"Detected {consecutive_errors} consecutive errors. Performing deep refresh...")
                                await self.deep_refresh()
                                consecutive_errors = 0
                                await asyncio.sleep(get_random_delay(30, 60))

                        # ブランド間の待機時間を調整
                        brand_wait_time = get_random_delay(8, 15)  # 待機時間を延長
                        self.logger.debug(
                            f"Waiting {brand_wait_time:.1f} seconds before next brand")
                        await asyncio.sleep(brand_wait_time)

                    except Exception as e:
                        self.logger.error(
                            f"Error processing brand {brand['name']}: {e}")
                        consecutive_errors += 1
                        if consecutive_errors >= 3:
                            self.logger.warning(
                                "Too many consecutive errors. Performing deep refresh...")
                            await self.deep_refresh()
                            consecutive_errors = 0
                            await asyncio.sleep(get_random_delay(30, 60))
                        continue

                # バッチ間で長めの待機
                batch_wait_time = get_random_delay(60, 120)  # 待機時間をさらに延長
                self.logger.info(
                    f"Batch {i//self.batch_size + 1} complete. Waiting {batch_wait_time:.1f} seconds before next batch...")
                await asyncio.sleep(batch_wait_time)

                # バッチ終了時に必ずdeep refresh
                await self.deep_refresh()

        except Exception as e:
            self.logger.error(f"Critical error in execute: {e}")
            self.logger.error(traceback.format_exc())
            raise

    async def should_refresh(self) -> bool:
        """ブラウザをリフレッシュすべきか判断"""
        current_time = time.time()

        # 時間経過によるリフレッシュ（5分）
        time_elapsed = current_time - self.last_refresh_time
        if time_elapsed > 300:  # 5分
            self.logger.info(
                f"Time-based refresh triggered after {time_elapsed:.1f} seconds")
            return True

        # ブランド数によるリフレッシュ（40ブランド）
        if self.brands_since_refresh >= 40:
            self.logger.info(
                f"Count-based refresh triggered after {self.brands_since_refresh} brands")
            return True

        return False

    async def refresh_browser(self):
        """ブラウザのリフレッシュ処理"""
        try:
            self.logger.info("Refreshing browser context")
            if self.context:
                await self.context.close()
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=UserAgent().random,
                java_script_enabled=True,
                bypass_csp=True,
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            )
            self.logger.info("Browser context refreshed")
        except Exception as e:
            self.logger.error(f"Error refreshing browser: {e}")

    async def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        try:
            self.logger.info("Cleaning up resources")
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def load_brand_files(self) -> List[Dict]:
        """ブランドデータファイルの読み込み（アルファベットでフィルタリング）"""
        all_brands = []
        # 指定されたアルファベットのファイルのみを処理
        file_path = self.brand_data_dir / \
            f'fragrantica_brands_{self.letter}.json'
        if file_path.exists():
            self.logger.info(f"Loading brand file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                brands = json.load(f)
                all_brands.extend(brands)
        return all_brands
