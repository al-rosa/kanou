from dataclasses import dataclass
from typing import Dict


@dataclass
class Brand:
    name: str
    url: str
    perfume_count: int
    page_number: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'Brand':
        return cls(
            name=data['name'],
            url=data['url'],
            perfume_count=data['perfume_count'],
            page_number=data['page_number']
        )

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'url': self.url,
            'perfume_count': self.perfume_count,
            'page_number': self.page_number
        }
