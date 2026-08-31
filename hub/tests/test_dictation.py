"""hub 逻辑测试：语音输入编排 STT→纠错→注入（DESIGN_OVERVIEW §8.6）。

用 fake 引擎，不依赖真实 STT/Windows 注入；CI（Linux）可跑。
"""
from hub.dictation import DictationOptions, DictationService
from hub.operator.correct import TextCorrector
from hub.operator.stt import SttEngine


class _FakeEngine(SttEngine):
    def name(self) -> str:
        return "fake"

    def transcribe(self, pcm, hotwords=None) -> str:
        return "在內,Passport倉庫上rebase一下主分支,然後提交PR。"


class _EmptyEngine(SttEngine):
    def name(self) -> str:
        return "empty"

    def transcribe(self, pcm, hotwords=None) -> str:
        return "   "


def test_dictation_correct_without_inject():
    svc = DictationService(
        _FakeEngine(), corrector=TextCorrector(),
        options=DictationOptions(inject="auto", correct=True),
    )
    res = svc.run([0] * 16000, inject=False)
    assert res.injected is False and res.method == ""
    assert "仓库" in res.corrected and "内" in res.corrected


def test_empty_transcription_not_injected():
    svc = DictationService(_EmptyEngine(), corrector=TextCorrector())
    res = svc.run([0] * 16000, inject=True)
    assert res.injected is False and res.corrected == ""


def test_correction_can_be_disabled():
    svc = DictationService(
        _FakeEngine(), corrector=TextCorrector(),
        options=DictationOptions(correct=False),
    )
    res = svc.run([0] * 16000, inject=False)
    assert res.corrected == res.raw
