from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AccordData:
    """香りのアコードの基本データクラス"""
    name: str
    strength: int


@dataclass
class SeasonData:
    """季節の適性の基本データクラス"""
    spring: bool = False
    summer: bool = False
    fall: bool = False
    winter: bool = False


@dataclass
class TimeOfDayData:
    """時間帯の適性の基本データクラス"""
    day: bool = False
    night: bool = False


@dataclass
class PerfumeData:
    """香水の基本データクラス"""
    name: str
    brand: str
    target_gender: List[str]
    main_accords: List[AccordData] = None
    seasons: SeasonData = None
    time_of_day: TimeOfDayData = None

    def __post_init__(self):
        """初期化後の処理"""
        if self.main_accords is None:
            self.main_accords = []
        if self.seasons is None:
            self.seasons = SeasonData()
        if self.time_of_day is None:
            self.time_of_day = TimeOfDayData()
