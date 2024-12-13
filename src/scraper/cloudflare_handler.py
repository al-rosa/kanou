
import asyncio
import logging
import random
import time

import requests
from playwright.async_api import Page


class CloudflareHandler:
    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger(__name__)

    async def test_connection(self) -> bool:
        """接続テスト"""
        try:
            # Torプロキシを使用してIPをチェック
            proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
            response = requests.get(
                'https://api.ipify.org?format=json', proxies=proxies)
            self.logger.info(f"Current IP: {response.json()['ip']}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    async def wait_for_challenge_completion(self, timeout: int = 60000) -> bool:
        """Cloudflareチャレンジ完了を待機（さらに改善版）"""
        try:
            start_time = time.time()
            check_interval = 2
            max_attempts = timeout / 1000 / check_interval

            for attempt in range(int(max_attempts)):
                # インタラクティブな要素の追加
                await self._perform_human_like_behavior()

                # ページコンテンツの確認
                if await self._verify_content():
                    return True

                await asyncio.sleep(check_interval)

                # 進捗ログ
                elapsed = time.time() - start_time
                self.logger.info(
                    f"Waiting for Cloudflare... {elapsed:.1f}s elapsed")

            return False

        except Exception as e:
            self.logger.error(f"Error in Cloudflare challenge: {e}")
            return False

    async def _perform_human_like_behavior(self):
        """人間らしい行動をシミュレート"""
        try:
            # ランダムなマウス移動
            await self.page.mouse.move(
                random.randint(100, 700),
                random.randint(100, 500)
            )

            # ランダムなスクロール
            await self.page.evaluate("""
                window.scrollTo({
                    top: Math.random() * document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)

            # 時々クリック
            if random.random() < 0.3:
                await self.page.mouse.click(
                    random.randint(100, 700),
                    random.randint(100, 500)
                )

            await asyncio.sleep(random.uniform(0.5, 2.0))

        except Exception as e:
            self.logger.debug(f"Error in human behavior simulation: {e}")

    async def _verify_content(self) -> bool:
        """ページコンテンツの検証（緩和版）"""
        try:
            # まずページのタイトルをチェック
            page_title = await self.page.title()
            if "Just a moment" in page_title:
                return False

            # Cloudflareの検出文字列をチェック
            page_text = await self.page.evaluate('document.body.innerText')
            cf_texts = [
                'checking your browser',
                'please wait',
                'please enable javascript',
                'please enable cookies',
                'security check to continue'
            ]

            if any(text.lower() in page_text.lower() for text in cf_texts):
                return False

            # 実際のコンテンツが存在するかチェック
            # より緩やかな条件に
            has_content = await self.page.evaluate("""
                () => {
                    // テキストコンテンツの存在確認
                    const hasText = document.body.innerText.length > 100;
                    
                    // 一般的なコンテナ要素の存在確認
                    const hasContainers = document.querySelectorAll('div').length > 5;
                    
                    // リンクの存在確認
                    const hasLinks = document.querySelectorAll('a').length > 0;
                    
                    return hasText && hasContainers && hasLinks;
                }
            """)

            return has_content

        except Exception as e:
            self.logger.debug(f"Error in content verification: {e}")
            # エラーの場合は、ページが読み込まれているものとして扱う
            return True
