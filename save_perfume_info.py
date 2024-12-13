import json
import re
from typing import Dict, Optional

from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    """テキストのクリーニング"""
    text = text.replace('&amp;', '&')  # HTMLエンティティの修正
    return ' '.join(text.strip().split())


def extract_concentration(soup: BeautifulSoup) -> Optional[str]:
    """製品タイプ（EDP/EDT）を様々な場所から探索"""
    # パターンとその完全な形式のマッピング
    concentration_map = {
        r'eau de parfum': 'Eau de Parfum',
        r'eau de toilette': 'Eau de Toilette',
        r'parfum': 'Parfum',
        r'cologne': 'Cologne',
        r'edc\b': 'Cologne',
        r'edp\b': 'Eau de Parfum',
        r'edt\b': 'Eau de Toilette'
    }

    # すべてのテキストノードを結合
    all_text = ' '.join(soup.stripped_strings).lower()

    # 最も長いパターンから検索（例：'eau de parfum' を 'parfum' より先に）
    for pattern, full_name in sorted(concentration_map.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(pattern, all_text):
            return full_name

    return None


def parse_perfume_info(html_path: str) -> Dict:
    """香水情報を解析"""
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    perfume_info = {
        "name": None,
        "year": None,
        "volumes": [],
        "brand": None,
        "concentration": None,
        "perfumers": [],
        "main_notes": []
    }

    try:
        # 商品名、年、ブランド名を説明文から取得
        description = soup.find('div', {'itemprop': 'description'})
        if description and description.find('b'):
            perfume_info["name"] = clean_text(description.find('b').text)
            perfume_info["brand"] = "Jo Malone London"

            # 説明文から年を取得
            desc_text = description.get_text()
            if year_match := re.search(r'\b(19|20)\d{2}\b', desc_text):
                perfume_info["year"] = int(year_match.group())

            # 説明文から調香師を取得
            if 'The nose behind this fragrance is' in desc_text:
                if perfumer_match := re.search(r'The nose behind this fragrance is ([^.]+)', desc_text):
                    perfume_info["perfumers"] = [
                        clean_text(perfumer_match.group(1))]

        # メインアコード（香調）を取得
        accords = []
        accord_bars = soup.find_all('div', class_='accord-bar')
        for bar in accord_bars:
            if text := bar.get_text().strip():
                accords.append(clean_text(text))
        perfume_info["main_notes"] = accords

        # 容量情報
        volume_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:ml|ML|мл)',
            r'(\d+(?:\.\d+)?)\s*(?:oz|OZ|унция)'
        ]
        desc_text = description.get_text() if description else ""
        volumes = set()
        for pattern in volume_patterns:
            if matches := re.finditer(pattern, desc_text):
                for match in matches:
                    volumes.add(f"{match.group(1)}ml")
        if volumes:
            perfume_info["volumes"] = sorted(list(volumes))

        # 製品タイプ（EDP/EDT）を取得
        perfume_info["concentration"] = extract_concentration(soup)

    except Exception as e:
        print(f"Error during parsing: {e}")

    return perfume_info


def save_perfume_info(info: Dict, output_path: str = 'perfume_info.json'):
    """香水情報をJSONとして保存"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"Information saved to {output_path}")


if __name__ == "__main__":
    html_path = 'perfume_page.html'
    perfume_info = parse_perfume_info(html_path)

    # 結果を表示
    print("\nExtracted Perfume Information:")
    print("-" * 50)
    for key, value in perfume_info.items():
        print(f"{key.title()}: {value}")

    # JSONとして保存
    save_perfume_info(perfume_info)
