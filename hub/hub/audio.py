"""音频输入：WAV 加载与格式校验（DESIGN_OVERVIEW §8.1）。

板端约定格式：16kHz / 16bit / mono PCM，约 32KB/s。
M0 用 WAV 文件仿真板子输入；板子到货后换成串口 PCM 流，格式校验复用。
"""

from __future__ import annotations

import struct
import tempfile
import wave
from pathlib import Path

SAMPLE_RATE = 16_000
CHANNELS = 1
BITS = 16


class AudioFormatError(ValueError):
    pass


def load_pcm_mono_16k(path: str | Path) -> list[int]:
    """读取 WAV 并校验为板端约定格式，返回 PCM 样本（list[int]）。"""
    p = Path(path)
    try:
        with wave.open(str(p), "rb") as w:
            if w.getframerate() != SAMPLE_RATE:
                raise AudioFormatError(
                    f"采样率不符：要求 {SAMPLE_RATE} Hz，实际 {w.getframerate()} Hz（请重采样后重试）"
                )
            if w.getnchannels() != CHANNELS:
                raise AudioFormatError(f"声道数不符：要求单声道，实际 {w.getnchannels()} 声道")
            if w.getsampwidth() != BITS // 8:
                raise AudioFormatError(f"位深不符：要求 16bit，实际 {w.getsampwidth() * 8} bit")
            frames = w.readframes(w.getnframes())
    except FileNotFoundError:
        raise
    except wave.Error as exc:
        raise AudioFormatError(f"打开 WAV 失败: {p}: {exc}") from exc

    pcm = list(struct.unpack(f"<{len(frames) // 2}h", frames))
    secs = len(pcm) / SAMPLE_RATE
    if secs > 120.0:
        raise AudioFormatError(f"音频过长（{secs:.1f}s > 120s），样本请控制在 2 分钟内")
    return pcm


def pcm_to_f32(pcm: list[int]) -> list[float]:
    """i16 PCM → f32（[-1.0, 1.0]），whisper 等引擎输入格式。"""
    return [s / 32768.0 for s in pcm]


def write_wav_sapi(path: str | Path, pcm: list[int]) -> None:
    """写 16k/16bit/mono WAV，供 System.Speech 的 SetInputToWaveFile。

    注意：SAPI 只认 WAVEFORMATEX（fmt chunk 18 字节、含 cbSize=0）；
    Python 标准库 wave 写的是 16 字节裸 PCM fmt，会被 SAPI 静默拒绝
    （识别返回空）。此坑在 Rust 版实测过，勿改回 wave 模块写文件。
    """
    data = struct.pack(f"<{len(pcm)}h", *pcm)
    data_len = len(data)
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 38 + data_len))
        f.write(b"WAVE")
        # fmt chunk（WAVEFORMATEX：18 字节 + cbSize=0）
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHHH", 18, 1, CHANNELS, SAMPLE_RATE, SAMPLE_RATE * 2, 2, BITS, 0))
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_len))
        f.write(data)


def temp_wav_path() -> str:
    return str(Path(tempfile.gettempdir()) / "boss-stt-debug.wav")
