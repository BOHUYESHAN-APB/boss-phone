"""系统级文字注入：把文本打到 Windows 当前前台光标处（DESIGN_OVERVIEW §8.6）。

“语音输入法”的落点：STT 转写 + 词表纠错后，把文字直接键入到当前前台应用的
编辑光标处——用户把光标放在哪里，文字就落在哪里。

两种注入方式（config.dictation.inject 切换）：
  type   逐字符 SendInput(KEYEVENTF_UNICODE)——不碰剪贴板，短文本首选
  paste  剪贴板 + Ctrl+V——快，长文本首选；自动保存/恢复原剪贴板
  auto   ≤paste_threshold 用 type，超过用 paste

健壮性：
  - SendInput 返回 0（UIPI 拦截 / 前台异常）→ 自动降级 paste
  - 无前台窗口（桌面/锁屏）→ InjectError 明确报错，不静默丢失文字
  - 非 Windows → InjectError
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_CONTROL = 0x11
VK_V = 0x56

_TYPE_CHUNK = 64  # 每批 SendInput 键入的字符数


class InjectError(RuntimeError):
    pass


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


def _is_windows() -> bool:
    return sys.platform == "win32"


def _send_input(*inputs: _INPUT) -> int:
    arr = (_INPUT * len(inputs))(*inputs)
    return ctypes.windll.user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))


def _key(vk: int, *, up: bool = False) -> _INPUT:
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    if up:
        inp.union.ki.dwFlags = KEYEVENTF_KEYUP
    return inp


def _unicode(char: str, *, up: bool = False) -> _INPUT:
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wScan = ord(char)
    inp.union.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
    return inp


def foreground_window_title() -> str | None:
    """当前前台窗口标题；桌面/锁屏时返回 None。"""
    if not _is_windows():
        return None
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return None
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value or None


def _clipboard_get() -> str | None:
    """读取当前剪贴板文本（用于注入后恢复）；空剪贴板返回 None。"""
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-Clipboard -Raw -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        raise InjectError(f"读取剪贴板失败: {exc}") from exc
    text = out.stdout
    return text.rstrip("\r\n") or None


def _clipboard_set(text: str) -> None:
    """写入剪贴板。走临时 UTF-8 BOM 文件，避免命令行超长/特殊字符问题。"""
    tmp = Path(tempfile.gettempdir()) / "boss-inject-clip.txt"
    tmp.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    cmd = f"Get-Content -Raw -Encoding UTF8 '{tmp}' | Set-Clipboard"
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            check=True,
            capture_output=True,
            timeout=10,
        )
    finally:
        tmp.unlink(missing_ok=True)


def _paste_via_ctrl_v() -> None:
    events = [_key(VK_CONTROL), _key(VK_V), _key(VK_V, up=True), _key(VK_CONTROL, up=True)]
    if _send_input(*events) == 0:
        raise InjectError("Ctrl+V 被拦截（UIPI/前台窗口异常）")


def type_text(text: str) -> None:
    """逐字符 SendInput(UNICODE) 键入文本，不触碰剪贴板。"""
    if not text:
        return
    chars = list(text)
    for i in range(0, len(chars), _TYPE_CHUNK):
        events: list[_INPUT] = []
        for ch in chars[i : i + _TYPE_CHUNK]:
            events.append(_unicode(ch))
            events.append(_unicode(ch, up=True))
        if _send_input(*events) == 0:
            raise InjectError("SendInput 被拦截（UIPI/前台窗口异常）")


def inject_text(text: str, mode: str = "auto", paste_threshold: int = 200) -> str:
    """把 text 注入当前前台光标处，返回实际使用的方式（type/paste）。"""
    if not _is_windows():
        raise InjectError("光标注入仅支持 Windows（当前非 Windows）")
    if not text:
        raise InjectError("注入文本为空")
    title = foreground_window_title()
    if title is None:
        raise InjectError("无前台窗口（可能是桌面/锁屏），无法定位光标")

    m = mode.lower()
    if m not in ("type", "paste", "auto"):
        raise InjectError(f"未知注入模式: {mode}（可选 type | paste | auto）")
    if m == "auto":
        m = "paste" if len(text) > paste_threshold else "type"

    if m == "type":
        try:
            type_text(text)
            return "type"
        except InjectError:
            # 键入被 UIPI 拦截 → 降级剪贴板粘贴，保证文字不丢
            m = "paste"

    if m == "paste":
        prev = _clipboard_get()
        try:
            _clipboard_set(text)
            _paste_via_ctrl_v()
        finally:
            if prev is not None:
                _clipboard_set(prev)
        return "paste"

    raise AssertionError("unreachable")
