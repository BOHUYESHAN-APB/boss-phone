"""STT 可插拔引擎层（DESIGN_OVERVIEW §8.2，从 M0 Rust 验证工具移植）。

三引擎全部声明、配置切换；统一输入为 16kHz/16bit/mono PCM（list[int]）。
专业术语（BWA/hg38/仓库名等）靠上层 LLM 词表纠错（§8.3），
引擎侧 hotwords 仅在引擎原生支持热词时注入（如 whisper initial_prompt）。

生产路径（§8.5 定稿）：本地 whisper 用 faster-whisper（同 ggml 模型，精度一致、加载更快）；
windows-native 引擎原样移植为 PowerShell 子进程实现。
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path

from hub.audio import pcm_to_f32, write_wav_sapi


class SttError(RuntimeError):
    pass


class EngineKind:
    WINDOWS = "windows"  # Windows 自带（System.Speech，PowerShell 子进程，零依赖）
    WHISPER = "whisper"  # faster-whisper 本地（需模型文件）
    CLOUD = "cloud"  # 云 API（M0 暂为 stub）


class SttEngine(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def transcribe(self, pcm: list[int], hotwords: list[str] | None = None) -> str: ...


class WindowsPsEngine(SttEngine):
    """windows-native：PowerShell 子进程调 System.Speech（SAPI 听写）。

    走子进程而非库内调用：System.Speech API 确定（SetInputToWaveFile 即离线文件识别），
    零第三方依赖。已知限制：中文听写质量一般、无热词——术语纠错交给上层 LLM 词表层。
    """

    timeout_secs = 10

    def name(self) -> str:
        return "windows-native"

    def transcribe(self, pcm: list[int], hotwords: list[str] | None = None) -> str:
        # System.Speech 只吃 WAV 文件：写临时 WAV（SAPI 专用 fmt）
        wav_path = Path(tempfile.gettempdir()) / "boss-stt-debug.wav"
        write_wav_sapi(wav_path, pcm)

        stamp = int(time.time() * 1000)
        ps1_path = Path(tempfile.gettempdir()) / f"boss-stt-{stamp}.ps1"
        script = f"""param([string]$WavPath)
Add-Type -AssemblyName System.Speech
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine([System.Globalization.CultureInfo]::GetCultureInfo('zh-CN'))
$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
$rec.SetInputToWaveFile($WavPath)
$texts = @()
while ($true) {{
    $r = $rec.Recognize([TimeSpan]::FromSeconds({self.timeout_secs // 2}))
    if (-not $r) {{ break }}
    $texts += $r.Text
}}
Write-Output ($texts -join '')
"""
        # UTF-8 BOM：Windows PowerShell 5.1 无 BOM 会按 ANSI 解析中文
        ps1_path.write_bytes(b"\xef\xbb\xbf" + script.encode("utf-8"))

        # LOCALAPPDATA 重定向：SAPI 会写 %LOCALAPPDATA%\Microsoft\Speech\Files\MSASR\*.dat
        # 适配缓存，沙箱/受限环境下该写会被拦截，识别静默返回空。重定向到临时目录绕开。
        fake_local = Path(tempfile.gettempdir()) / f"boss-stt-sapi-{stamp}"
        fake_local.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "LOCALAPPDATA": str(fake_local)}

        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1_path),
                    str(wav_path),
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=self.timeout_secs + 30,
                check=False,
            )
        except FileNotFoundError as exc:
            raise SttError("未找到 powershell，windows-native 引擎需要 Windows") from exc
        except subprocess.TimeoutExpired as exc:
            raise SttError("PowerShell 识别超时") from exc
        finally:
            ps1_path.unlink(missing_ok=True)  # 保留 WAV 供 diag 复测

        if proc.returncode != 0:
            raise SttError(f"PowerShell 识别失败（exit {proc.returncode}）：{proc.stderr.strip()}")
        return proc.stdout.strip()


class WhisperEngine(SttEngine):
    """whisper-local：faster-whisper（CTranslate2 后端），生产 STT 主引擎。

    与 M0 Rust whisper-rs 验证工具同 ggml 模型，精度一致；initial_prompt 注入热词。
    """

    def __init__(self, model_path: str | None = None, *, language: str = "zh"):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover
            raise SttError("whisper 引擎未安装：pip install 'faster-whisper>=1.0'") from exc
        path = model_path or "base"  # 留空用 HuggingFace 默认 small/base
        self._model = WhisperModel(path, device="cpu", compute_type="int8")
        self._language = language

    def name(self) -> str:
        return "whisper-local"

    def transcribe(self, pcm: list[int], hotwords: list[str] | None = None) -> str:
        initial_prompt = ", ".join(hotwords) if hotwords else None
        segments, _info = self._model.transcribe(
            pcm_to_f32(pcm),
            language=self._language,
            beam_size=1,
            initial_prompt=initial_prompt,
        )
        return "".join(seg.text for seg in segments).strip()


class CloudEngine(SttEngine):
    """cloud-api：M0 暂为 stub，选定服务商（字节火山/讯飞/OpenAI）后实装。"""

    def name(self) -> str:
        return "cloud-api"

    def transcribe(self, pcm: list[int], hotwords: list[str] | None = None) -> str:
        raise SttError("cloud-api 引擎 M0 未实装（待选定服务商：字节火山/讯飞/OpenAI）")


def create_engine(kind: str, model_path: str | None = None) -> SttEngine:
    k = kind.lower()
    if k in ("windows", "windows-native"):
        return WindowsPsEngine()
    if k in ("whisper", "whisper-local"):
        return WhisperEngine(model_path)
    if k in ("cloud", "cloud-api"):
        return CloudEngine()
    raise SttError(f"未知引擎: {kind}（可选：windows | whisper | cloud）")
