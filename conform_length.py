import json
from pathlib import Path


def count_brands_by_group():
    data_dir = Path('data')
    counts = {}

    # A-Z
    ae_count = 0
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        file_path = data_dir / f'fragrantica_brands_{letter}.json'
        if file_path.exists():
            with open(file_path, 'r') as f:
                brands = json.load(f)
                ae_count += len(brands)
        counts[letter] = ae_count

    return counts

# 必要なバッチ数を計算


def calculate_required_batches(brand_counts, batch_size=50):
    required_batches = {}
    for group, count in brand_counts.items():
        batches = (count + batch_size - 1) // batch_size  # 切り上げ除算
        required_batches[group] = batches
    return required_batches


def main():
    brand_counts = count_brands_by_group()
    print("Brand counts by group:", brand_counts)

    batch_size = 50
    required_batches = calculate_required_batches(brand_counts, batch_size)
    print("\nRequired batches by group:", required_batches)


if __name__ == "__main__":
    main()
