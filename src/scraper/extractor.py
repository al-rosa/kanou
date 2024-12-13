from typing import Dict, List

from playwright.async_api import Page


async def extract_brands_data(page: Page, grid_selector: str) -> List[Dict]:
    """ブランドデータの抽出"""
    js_code = """
    (selector) => {
        return Array.from(document.querySelectorAll(selector + ' div.designerlist')).map(el => {
            const link = el.querySelector('a');
            const badge = el.querySelector('.badge');
            if (link && badge) {
                return {
                    name: link.textContent.trim(),
                    url: link.href,
                    perfume_count: parseInt(badge.textContent)
                };
            }
            return null;
        }).filter(item => item !== null);
    }
    """
    return await page.evaluate(js_code, grid_selector)
