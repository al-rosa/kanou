import asyncio

from playwright.async_api import Page


async def verify_cloudflare_passed(page: Page) -> bool:
    """Cloudflareチェック通過の確認"""
    try:
        for _ in range(30):  # 30秒待機
            try:
                page_text = await page.evaluate('document.body.innerText')

                # Cloudflareの検出文字列
                cf_texts = [
                    'checking your browser',
                    'cloudflare',
                    'please wait',
                    'please enable javascript',
                    'please enable cookies',
                    'security check',
                    'just a moment'  # これも追加
                ]

                if not any(text.lower() in page_text.lower() for text in cf_texts):
                    # サイトのコンテンツを確認
                    content_selectors = [
                        'div.accord-bar',
                        'h6:text("main accords")',
                        'div.grid-x',
                        'h1'
                    ]

                    for selector in content_selectors:
                        element = await page.query_selector(selector)
                        if element:
                            print("Content detected, Cloudflare check passed")
                            return True

                print("Waiting for content to load...")
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Error during verification: {e}")
                await asyncio.sleep(1)

        print("Content verification timed out")
        return False

    except Exception as e:
        print(f"Error in verify_cloudflare_passed: {str(e)}")
        return False
