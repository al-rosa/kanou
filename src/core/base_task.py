# src/core/base_task.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTask(ABC):
    """
    基本タスククラス
    全てのタスクの基底クラスとして使用される
    """

    @abstractmethod
    async def setup(self) -> None:
        """
        タスクの実行前の初期化処理
        リソースの確保やコネクションの確立など
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Dict[str, Any]) -> None:
        """
        タスクのメイン処理
        実際の処理はこのメソッドに実装する
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        タスクの終了時のクリーンアップ処理
        リソースの解放など
        """
        pass

    async def run(self, **kwargs: Dict[str, Any]) -> None:
        """
        タスクの実行フロー制御
        setupとcleanupを適切に行う
        """
        try:
            await self.setup()
            await self.execute(**kwargs)
        finally:
            await self.cleanup()
