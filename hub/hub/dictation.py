"""语音输入编排（DESIGN_OVERVIEW §8.6）：STT → 词表纠错 → 光标注入。

这是"板子长按 OK 说话 → 文字落到 PC 光标处"链路的 PC 侧实现与验证入口。
STT 是 CPU 密集（whisper），调用方应放 asyncio.to_thread；本模块保持同步可测。

健壮性约定（§8.6）：
  - 空转写不注入，返回 injected=False，不静默造字
  - 注入失败明确记录，但不阻断整条链路（STT 结果仍可查看）
  - 纠错层可开关（--no-correct），度量纠错收益（§8.4 任务 3）
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import NamedTuple

from hub.input.inject import InjectError, inject_text
from hub.operator.correct import TextCorrector
from hub.operator.stt import SttEngine


class DictationResult(NamedTuple):
    raw: str          # STT 原始转写
    corrected: str    # 词表纠错后
    injected: bool    # 是否成功注入光标处
    method: str       # 实际注入方式（type / paste / ""）
    elapsed: float    # 转写耗时（秒）


@dataclass
class DictationOptions:
    inject: str = "auto"       # type | paste | auto（见 input/inject）
    paste_threshold: int = 200  # auto：超过该长度走剪贴板粘贴
    correct: bool = True        # 词表纠错层开关（度量收益用）


class DictationService:
    def __init__(
        self,
        engine: SttEngine,
        corrector: TextCorrector | None = None,
        hotwords: list[str] | None = None,
        options: DictationOptions | None = None,
    ) -> None:
        self.engine = engine
        self.corrector = corrector
        self.hotwords = hotwords or []
        self.options = options or DictationOptions()

    def transcribe(self, pcm: list[int]) -> str:
        return self.engine.transcribe(pcm, self.hotwords).strip()

    def correct(self, text: str) -> str:
        if not self.options.correct or not self.corrector:
            return text
        return self.corrector.correct(text)

    def run(self, pcm: list[int], *, inject: bool = True) -> DictationResult:
        """完整链路：STT → 纠错 → 注入。inject=False 时只转写+纠错（度量用）。"""
        t0 = time.monotonic()
        raw = self.transcribe(pcm)
        corrected = self.correct(raw)
        elapsed = time.monotonic() - t0

        method = ""
        injected = False
        if inject and corrected:
            try:
                method = inject_text(
                    corrected, mode=self.options.inject, paste_threshold=self.options.paste_threshold
                )
                injected = True
            except InjectError as exc:
                print(f"[dictation] 光标注入失败（不阻断）：{exc}")
        return DictationResult(raw, corrected, injected, method, elapsed)
