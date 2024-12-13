import json
from pathlib import Path
from typing import List

from config.settings import OUTPUT_DIR
from models.brand import Brand


class JsonStorage:
    @staticmethod
    def save_brands(brands: List[Brand], letter: str) -> None:
        """ブランド情報をJSONファイルとして保存"""
        OUTPUT_DIR.mkdir(exist_ok=True)
        filename = OUTPUT_DIR / f'fragrantica_brands_{letter}.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(
                [brand.to_dict() for brand in brands],
                f,
                ensure_ascii=False,
                indent=2
            )
        print(f"Saved brands for letter {letter} to {filename}")
