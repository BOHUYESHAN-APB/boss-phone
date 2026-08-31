"""接线员 LLM provider 接口（DESIGN_HUB §5，骨架）。

接线员本身是 Hub 内的一个任务，通过可替换 provider 接口接入模型：
  - 多模态直听（audio → 意图）
  - 两段式（STT → LLM）
备忘录转写与接线员共用 provider 以降成本。M1 实装。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LlmProvider(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def audio_to_intent(self, audio_pcm: list[int]) -> dict:
        """多模态直听：音频 → {transcript, intent, route}（M1）"""
        ...

    @abstractmethod
    async def text_to_intent(self, text: str) -> dict:
        """两段式：转写文本 → 意图路由（M1）"""
        ...
