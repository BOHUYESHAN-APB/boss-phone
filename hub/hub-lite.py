#!/usr/bin/env python3
"""hub-lite：M0 语音链路验证 + 语音输入法入口（DESIGN_OVERVIEW §8.4/§8.6）。

WAV 文件 → 16k PCM → STT 引擎（可切换）→ 词表纠错 → （可选）打到当前光标处。
板子到货后，输入源换成串口 PCM（hub serve 正式网关），STT/纠错/注入层复用。

用法：
  python hub/hub-lite.py <样本.wav> [--engine windows|whisper|cloud]
                                     [--model <模型路径>] [--hotwords 词1,词2]
                                     [--type]        # 语音输入法：文字落到当前光标处
                                     [--inject type|paste|auto]
                                     [--no-correct]  # 关词表纠错，度量纠错收益
                                     [--terms <用户词表.json>]
                                     [--selftest]    # 仅检查注入能力（不发字）
"""

from __future__ import annotations

import argparse
import sys
import time

from hub.audio import SAMPLE_RATE, load_pcm_mono_16k
from hub.dictation import DictationOptions, DictationService
from hub.input.inject import foreground_window_title
from hub.operator.correct import TextCorrector
from hub.operator.stt import create_engine


def _cmd_selftest() -> int:
    """注入能力自检：前台窗口存在性 + SendInput 可用性（不发字）。"""
    print("== 注入自检（不发送任何文字）==")
    title = foreground_window_title()
    if title is None:
        print("  ✗ 无前台窗口（桌面/锁屏），无法注入。请先聚焦一个编辑窗口再试。")
        return 1
    print(f"  ✓ 前台窗口: {title!r}")
    try:
        from hub.input.inject import _send_input, _unicode

        n = _send_input(_unicode("\u200b"))  # 零宽空格：仅验证 API 通路，无可见效果
        if n == 0:
            print("  ✗ SendInput 被拦截（UIPI），注入可能失败。")
            return 1
        print("  ✓ SendInput API 可用（UIPI 未拦截）")
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ SendInput 异常: {exc}")
        return 1
    print("注入能力正常。把光标放在目标编辑处，用 --type 即可语音输入。")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hub-lite", description="M0 语音链路验证 + 语音输入法")
    p.add_argument("wav", nargs="?", help="16kHz/16bit/mono WAV 样本（--selftest 时可不带）")
    p.add_argument("--engine", default="windows", choices=["windows", "whisper", "cloud"],
                   help="STT 引擎（默认 windows）")
    p.add_argument("--model", default=None, help="whisper 引擎的模型路径/名称（默认 base）")
    p.add_argument("--hotwords", default="", help="热词/词表（逗号分隔，注入 initial_prompt）")
    p.add_argument("--type", action="store_true", dest="type_",
                   help="语音输入法模式：纠错后的文字直接打到当前光标处")
    p.add_argument("--inject", default="auto", choices=["type", "paste", "auto"],
                   help="注入方式（默认 auto：短文本逐字、长文本剪贴板）")
    p.add_argument("--no-correct", action="store_true", help="关闭词表纠错层（度量收益）")
    p.add_argument("--terms", default=None, help="用户词表 JSON（热更新）")
    p.add_argument("--selftest", action="store_true", help="仅注入能力自检，不识别音频")
    args = p.parse_args(argv)

    if args.selftest:
        return _cmd_selftest()
    if not args.wav:
        p.error("需要 WAV 样本（或使用 --selftest）")

    hotwords = [w.strip() for w in args.hotwords.split(",") if w.strip()]
    corrector = TextCorrector.from_json(args.terms) if args.terms else TextCorrector()

    print("== BOSS PHONE hub-lite（语音链路验证 / 语音输入法）==")
    print(f"WAV     : {args.wav}")
    print(f"引擎    : {args.engine}")
    if hotwords:
        print(f"热词    : {' / '.join(hotwords)}")
    print(f"纠错层  : {'关' if args.no_correct else '开'}")
    if args.type_:
        print(f"注入    : {args.inject}（文字落到当前光标处）")
        title = foreground_window_title()
        print(f"光标位置: {title!r}（请确认已聚焦目标编辑窗口）")

    # 1. 加载并校验音频（板端格式契约：16k/16bit/mono）
    pcm = load_pcm_mono_16k(args.wav)
    print(f"音频    : {len(pcm) / SAMPLE_RATE:.1f}s / {len(pcm)} 样本")

    # 2. 构建服务：STT → 纠错 → 注入
    service = DictationService(
        create_engine(args.engine, args.model),
        corrector=corrector,
        hotwords=hotwords,
        options=DictationOptions(inject=args.inject, correct=not args.no_correct),
    )
    print(f"转写中  : {service.engine.name()}")

    # 3. 跑完整链路（CPU 密集，whisper 场景下生产端放 to_thread）
    result = service.run(pcm, inject=args.type_)

    print("----------------------------------------")
    print(f"耗时    : {result.elapsed:.2f}s")
    print("原始转写:")
    print(result.raw or "（空）")
    if args.no_correct:
        print("（纠错层已关闭）")
    else:
        print("纠错后  :")
        print(result.corrected or "（空）")
    if args.type_:
        if result.injected:
            print(f"已注入  : ✓（{result.method}，光标处）")
        else:
            print("已注入  : ✗（见上方失败原因）")
    print("----------------------------------------")
    return 0


if __name__ == "__main__":
    sys.exit(main())
