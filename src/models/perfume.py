# src/models/perfume.py
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Accord:
    """香りのアコード"""
    name: str
    strength: int

    @classmethod
    def from_dict(cls, data: Dict) -> 'Accord':
        return cls(
            name=data['name'],
            strength=data['strength']
        )

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'strength': self.strength
        }


@dataclass
class Season:
    """季節の適性"""
    spring: bool = False
    summer: bool = False
    fall: bool = False
    winter: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> 'Season':
        return cls(**data)

    def to_dict(self) -> Dict:
        return {
            'spring': self.spring,
            'summer': self.summer,
            'fall': self.fall,
            'winter': self.winter
        }


@dataclass
class TimeOfDay:
    """時間帯の適性"""
    day: bool = False
    night: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> 'TimeOfDay':
        return cls(**data)

    def to_dict(self) -> Dict:
        return {
            'day': self.day,
            'night': self.night
        }


@dataclass
class Perfume:
    """香水データ"""
    name: str
    brand: str
    target_gender: List[str]
    main_accords: List[Accord]
    seasons: Season
    time_of_day: TimeOfDay

    @classmethod
    def from_dict(cls, data: Dict) -> 'Perfume':
        return cls(
            name=data['name'],
            brand=data['brand'],
            target_gender=data['target_gender'],
            main_accords=[Accord.from_dict(accord)
                          for accord in data['main_accords']],
            seasons=Season.from_dict(data['seasons']),
            time_of_day=TimeOfDay.from_dict(data['time_of_day']),
        )

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'brand': self.brand,
            'target_gender': self.target_gender,
            'main_accords': [accord.to_dict() for accord in self.main_accords],
            'seasons': self.seasons.to_dict(),
            'time_of_day': self.time_of_day.to_dict(),
        }
