import random

from config.settings import SCRAPING_CONFIG


def get_random_delay(min_delay: float, max_delay: float) -> float:
    """より人間らしい遅延時間の生成"""
    # ガウス分布を使用してより自然な遅延を生成
    mean = (min_delay + max_delay) / 2
    std = (max_delay - min_delay) / 4
    delay = random.gauss(mean, std)
    return max(min_delay, min(max_delay, delay))


def normalize_url(url: str) -> str:
    """URLの正規化"""
    return (
        f"https://www.fragrantica.com{url}"
        if url.startswith('/')
        else url
    )
