"""帧封装（DESIGN_PROTOCOL §4，链路无关）。

同一传输流上两种帧按 magic 区分：
  控制帧（JSON）：{envelope_json}\\n            # magic 隐含：以 { 开头
  媒体帧（二进制）：MAGIC(2B)|TYPE(1B)|FLAGS(1B)|LEN(2B, 大端)|PAYLOAD
MAGIC = 0xAA 0x55；TYPE：0x01 voice / 0x02 audio / 0x03 file-data / 0x04 file-meta。

CDC 用字节流解析（\\n 或 magic+len）；WS 用 text/binary 天然分帧，
但控制帧内容与字段定义同一套，编解码函数复用。
"""

from __future__ import annotations

import json
import struct
import time
from typing import NamedTuple

MAGIC = b"\xaa\x55"
MAGIC_HEADER_LEN = 6  # MAGIC(2) + TYPE(1) + FLAGS(1) + LEN(2)

TYPE_VOICE = 0x01
TYPE_AUDIO = 0x02
TYPE_FILE_DATA = 0x03
TYPE_FILE_META = 0x04
TYPE_NAMES = {
    TYPE_VOICE: "voice",
    TYPE_AUDIO: "audio",
    TYPE_FILE_DATA: "file-data",
    TYPE_FILE_META: "file-meta",
}

FLAG_FIRST = 0x02  # 分片首段
FLAG_FINAL = 0x01  # 末段


class MediaFrame(NamedTuple):
    type: int
    flags: int
    payload: bytes

    @property
    def type_name(self) -> str:
        return TYPE_NAMES.get(self.type, f"0x{self.type:02x}")


def make_envelope(type_: str, to: str, seq: int, payload: dict, *, from_: str = "hub") -> dict:
    """统一信封（DESIGN_PROTOCOL §2）。"""
    return {
        "type": type_,
        "from": from_,
        "to": to,
        "seq": seq,
        "ts": int(time.time() * 1000),
        "payload": payload,
    }


def encode_control(msg: dict) -> bytes:
    """JSON 控制帧：{json}\\n（magic 隐含：以 { 开头）。"""
    return (json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def encode_media(type_: int, flags: int, payload: bytes) -> bytes:
    return MAGIC + bytes([type_, flags]) + struct.pack(">H", len(payload)) + payload


class FrameParser:
    """CDC 字节流分帧：\\n 结束的 JSON 控制帧 + magic+len 媒体帧。

    `feed` 每次返回一批 (kind, obj)，kind ∈ {"control", "media", "error"}；
    未凑齐的帧留在内部缓冲，等下一段数据。
    """

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[tuple[str, object]]:
        self._buf.extend(data)
        out: list[tuple[str, object]] = []
        while True:
            if not self._buf:
                break
            if self._buf[0] == ord("{"):
                nl = self._buf.find(b"\n")
                if nl < 0:
                    break  # JSON 未结束，等下一段
                line = bytes(self._buf[:nl])
                del self._buf[: nl + 1]
                try:
                    out.append(("control", json.loads(line.decode("utf-8"))))
                except (ValueError, UnicodeDecodeError) as exc:
                    out.append(("error", f"bad-json: {exc}"))
                continue
            if self._buf[:2] == MAGIC:
                if len(self._buf) < MAGIC_HEADER_LEN:
                    break  # 头未齐
                type_, flags = self._buf[2], self._buf[3]
                (length,) = struct.unpack(">H", self._buf[4:6])
                if len(self._buf) < MAGIC_HEADER_LEN + length:
                    break  # 载荷未齐
                payload = bytes(self._buf[MAGIC_HEADER_LEN : MAGIC_HEADER_LEN + length])
                del self._buf[: MAGIC_HEADER_LEN + length]
                out.append(("media", MediaFrame(type_, flags, payload)))
                continue
            # 残渣：既非 { 也非 magic，丢 1 字节重同步
            del self._buf[0]
        return out
