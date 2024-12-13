from pathlib import Path

# ブラウザ設定
BROWSER_CONFIG = {
    'viewport': {'width': 1920, 'height': 1080},
    'java_script_enabled': True,
}

# スクレイピング設定
SCRAPING_CONFIG = {
    'max_retries': 3,
    'timeout': 30000,
    'min_delay': 2,
    'max_delay': 5,
}

# 出力設定
OUTPUT_DIR = Path('/app/data')
