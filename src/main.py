# src/main.py
import asyncio
import logging
import os

from tasks.brand_scraping import BrandScrapingTask
from tasks.fragrance_basic_scraping import FragranceBasicScrapingTask
from tasks.perfume_detail_scraping import PerfumeDetailScrapingTask
from utils.logger import setup_logger


async def main():
    """メインエントリーポイント"""
    try:
        # ロギングの設定
        setup_logger()
        logger = logging.getLogger(__name__)

        # タスクの種類を環境変数から取得
        task_name = os.getenv('TASK_NAME', 'brand_scraping')
        logger.info(f"Starting task: {task_name}")

        # タスクの初期化
        if task_name == 'brand_scraping':
            letter_group = int(os.getenv('LETTER_GROUP', 1))
            task = BrandScrapingTask(letter_group)
        elif task_name == 'perfume_detail_scraping':  # タスク名を修正
            task = PerfumeDetailScrapingTask(
                delay_min=float(os.getenv('SCRAPING_DELAY_MIN', 2)),
                delay_max=float(os.getenv('SCRAPING_DELAY_MAX', 4)),
                max_retries=int(os.getenv('MAX_RETRIES', 3))
            )
        elif task_name == 'fragrance_basic_scraping':
            letter = os.getenv('LETTER')  # 環境変数から単一のアルファベットを取得
            if not letter:
                raise ValueError("LETTER environment variable is required")

            task = FragranceBasicScrapingTask(
                delay_min=float(os.getenv('SCRAPING_DELAY_MIN', 1)),
                delay_max=float(os.getenv('SCRAPING_DELAY_MAX', 2)),
                max_retries=int(os.getenv('MAX_RETRIES', 3)),
                letter=letter,
                batch_size=int(os.getenv('BATCH_SIZE', 50))
            )
        else:
            raise ValueError(f"Unknown task: {task_name}")

        try:
            await task.run()
        finally:
            await task.cleanup()

    except Exception as e:
        logging.error(f"Application error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
