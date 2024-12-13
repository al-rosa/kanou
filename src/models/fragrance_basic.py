# models/fragrance_basic.py
from dataclasses import dataclass
from typing import Dict


@dataclass
class FragranceBasicInfo:
    brand_name: str
    perfume_name: str
    url: str

    def to_dict(self) -> Dict:
        return {
            'brand_name': self.brand_name,
            'perfume_name': self.perfume_name,
            'url': self.url
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FragranceBasicInfo':
        return cls(
            brand_name=data['brand_name'],
            perfume_name=data['perfume_name'],
            url=data['url']
        )
