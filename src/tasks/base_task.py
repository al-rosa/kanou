from abc import ABC, abstractmethod


class BaseTask(ABC):
    """基本タスククラス"""

    @abstractmethod
    async def execute(self, **kwargs):
        """タスクの実行"""
        pass

    @abstractmethod
    async def cleanup(self):
        """リソースのクリーンアップ"""
        pass
