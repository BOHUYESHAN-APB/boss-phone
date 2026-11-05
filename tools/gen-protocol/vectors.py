#!/usr/bin/env python3
"""协议黄金向量生成器（DESIGN_TEST L2：协议一致性门禁）。

黄金向量 = 人工审定的信封语义（envelope）+ 工具计算的线上字节（wire_hex）。
四端（C/Rust/Kotlin/Python）实现编解码时，一律以 `protocol/vectors/golden.json`
为共同比对基准——`generate.mjs --check` 只保证四端结构声明同源，本向量才保证
"同一条消息在各端编出相同字节、解回相同语义"。

字节基准（与 hub.gateway.framing 一致，此处独立实现即"可执行规格"）：
  控制帧：UTF-8 紧凑 JSON（ensure_ascii=False, separators=(",",":")）+ "\\n"
  媒体帧：AA55 | TYPE(1B) | FLAGS(1B) | LEN(2B 大端) | PAYLOAD

用法：
  python tools/gen-protocol/vectors.py          # 重新生成 golden.json
  python tools/gen-protocol/vectors.py --check  # CI 校验：wire_hex 与信封是否同步

新增消息时：在下方 *_VECTORS 补一条向量 → 重跑本脚本提交 golden.json。
Python/Rust 两端测试读 golden.json 自动纳入新向量；C/Kotlin 端待各自
编解码落地（C 在固件 Rust 层、Kotlin 在 M2）后接入同一文件。
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

# Windows 控制台默认 GBK（cp936），中文提示与全角标点会抛 UnicodeEncodeError。
# 显式切到 UTF-8，保证本地与 CI 输出一致可读。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "protocol" / "vectors" / "golden.json"

MAGIC = b"\xaa\x55"
TYPE_VOICE, TYPE_AUDIO, TYPE_FILE_DATA, TYPE_FILE_META = 0x01, 0x02, 0x03, 0x04
FLAG_FIRST, FLAG_FINAL = 0x02, 0x01

# 固定时间戳：黄金向量必须字节级确定，ts 不取当前时间
TS = 1756000000000
DEVICE = "passport:AA:BB:CC:DD:EE:FF"
AGENT = "boss-phone"


def env(type_: str, from_: str, to: str, seq: int, payload: dict, ts: int = TS) -> dict:
    """统一信封（DESIGN_PROTOCOL §2），字段顺序即线上字节顺序。"""
    return {"type": type_, "from": from_, "to": to, "seq": seq, "ts": ts, "payload": payload}


CONTROL_VECTORS: list[dict] = [
    {
        "name": "hello-minimal",
        "schema": "hello",
        "envelope": env("hello", "device", "hub", 1, {
            "proto": 1, "device": DEVICE, "fw": "0.1.0",
            "caps": ["voice.stt", "state.push"],
        }),
    },
    {
        # 断线重连补收：resume_seq 可选字段出现
        "name": "hello-resume",
        "schema": "hello",
        "envelope": env("hello", "device", "hub", 1, {
            "proto": 1, "device": DEVICE, "fw": "0.1.0",
            "caps": ["voice.stt", "state.push"], "resume_seq": 128,
        }),
    },
    {
        "name": "hello-ack",
        "schema": "hello_ack",
        "envelope": env("hello_ack", "hub", "device", 1, {
            "proto": 1, "caps": ["voice.stt", "state.push", "ring", "memo"],
            "device_id": DEVICE, "server_time": TS + 123,
        }),
    },
    {
        "name": "presence-online",
        "schema": "presence",
        "envelope": env("presence", f"agent:{AGENT}", "hub", 7, {
            "agent_id": AGENT, "online": True, "cli": "claude-code",
            "cwd": "/home/dev/boss-phone", "caps": ["permission_ask", "usage"],
        }),
    },
    {
        "name": "presence-offline",
        "schema": "presence",
        "envelope": env("presence", f"agent:{AGENT}", "hub", 8, {
            "agent_id": AGENT, "online": False, "cli": "claude-code",
            "cwd": "/home/dev/boss-phone", "caps": [],
        }),
    },
    {
        # 可选字段 task 出现（等待输入：黄灯场景）
        "name": "state-waiting-task",
        "schema": "state",
        "envelope": env("state", f"agent:{AGENT}", "device", 42, {
            "agent_id": AGENT, "state": "waiting_input",
            "summary": "等待选择：是否允许写入 src/？", "task": "重构 CI", "since": TS,
        }),
    },
    {
        # 可选字段 task 缺省（阻塞：红灯场景，中文摘要验证 UTF-8 字节）
        "name": "state-blocked",
        "schema": "state",
        "envelope": env("state", f"agent:{AGENT}", "device", 43, {
            "agent_id": AGENT, "state": "blocked",
            "summary": "CI 失败：clippy 报错 3 处", "since": TS,
        }),
    },
    {
        # 嵌套结构：单选 + input（带 default）混合
        "name": "ask-mixed",
        "schema": "ask",
        "envelope": env("ask", f"agent:{AGENT}", "device", 7, {
            "ask_id": "u-0001", "agent_id": AGENT, "reason": "需要写权限",
            "questions": [
                {"q_no": 1, "kind": "single", "prompt": "允许写入 src/ 吗？",
                 "options": ["允许", "拒绝"], "optional": False},
                {"q_no": 2, "kind": "input", "prompt": "备注",
                 "options": [], "optional": True, "default": "无"},
            ],
        }),
    },
    {
        # 对 ask 的回答：单选 selection 单元素 + input text 补全
        "name": "answer-multi",
        "schema": "answer",
        "envelope": env("answer", "device", "hub", 3, {
            "ask_id": "u-0001",
            "answers": [
                {"q_no": 1, "kind": "single", "selection": [0]},
                {"q_no": 2, "kind": "input", "selection": [], "text": "无备注"},
            ],
            "answered_by": "device", "ts": TS,
        }),
    },
    {
        # 红色报警：summary 必带，ringtone 缺省
        "name": "ring-red-alert",
        "schema": "ring",
        "envelope": env("ring", "hub", "device", 2, {
            "ring_id": "r-0001", "agent_id": AGENT, "kind": "red_alert",
            "reason": "CI 失败", "summary": "clippy 报错 3 处",
        }),
    },
    {
        # Agent 来电：可选 ringtone 出现
        "name": "ring-agent-call",
        "schema": "ring",
        "envelope": env("ring", "hub", "device", 3, {
            "ring_id": "r-0002", "agent_id": AGENT, "kind": "agent_call",
            "reason": "任务完成，请确认", "ringtone": "chime",
        }),
    },
    {
        "name": "ring-ack-accept",
        "schema": "ring_ack",
        "envelope": env("ring_ack", "device", "hub", 4, {
            "ring_id": "r-0002", "accept": True,
        }),
    },
    {
        "name": "ring-ack-reject",
        "schema": "ring_ack",
        "envelope": env("ring_ack", "device", "hub", 4, {
            "ring_id": "r-0002", "accept": False,
        }),
    },
    {
        "name": "hangup-error",
        "schema": "hangup",
        "envelope": env("hangup", "hub", "device", 5, {
            "call_id": "r-0002", "reason": "error",
        }),
    },
]

MEDIA_VECTORS: list[dict] = [
    # 单段完整语音：FIRST|FINAL
    {"name": "voice-single", "type": TYPE_VOICE, "flags": FLAG_FIRST | FLAG_FINAL,
     "payload_hex": bytes(range(32)).hex()},
    # 分片首段
    {"name": "voice-first", "type": TYPE_VOICE, "flags": FLAG_FIRST,
     "payload_hex": bytes(range(16)).hex()},
    # 中段无标志；300B 载荷验证 LEN 两字节大端（>0xFF）
    {"name": "audio-mid", "type": TYPE_AUDIO, "flags": 0,
     "payload_hex": (bytes(range(256)) + bytes(range(44))).hex()},
    # 文件数据末段
    {"name": "file-data-final", "type": TYPE_FILE_DATA, "flags": FLAG_FINAL,
     "payload_hex": b"\xde\xad\xbe\xef\xca\xfe\xba\xbe".hex()},
    # 空载荷边界：LEN=0
    {"name": "file-meta-empty", "type": TYPE_FILE_META, "flags": 0, "payload_hex": ""},
]


def encode_control(msg: dict) -> bytes:
    """与 hub.gateway.framing.encode_control 相同的可执行规格（独立实现防漂移）。"""
    return (json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def encode_media(type_: int, flags: int, payload: bytes) -> bytes:
    return MAGIC + bytes([type_, flags]) + struct.pack(">H", len(payload)) + payload


def build() -> dict:
    controls = [
        {**v, "wire_hex": encode_control(v["envelope"]).hex()} for v in CONTROL_VECTORS
    ]
    media = [
        {**v, "wire_hex": encode_media(v["type"], v["flags"], bytes.fromhex(v["payload_hex"])).hex()}
        for v in MEDIA_VECTORS
    ]
    # 混排流：控制帧与媒体帧同一条字节流（CDC 字节流分帧的典型形态）
    by_name = {c["name"]: c for c in controls}
    stream_hex = (
        by_name["hello-minimal"]["wire_hex"]
        + next(m["wire_hex"] for m in media if m["name"] == "voice-single")
        + by_name["state-blocked"]["wire_hex"]
    )
    streams = [{
        "name": "cdc-mixed",
        "wire_hex": stream_hex,
        "expect": ["control:hello", "media:voice", "control:state"],
    }]
    return {
        "_comment": "GENERATED by tools/gen-protocol/vectors.py — DO NOT EDIT（语义 SSOT 在该脚本，改动后重新生成提交）",
        "control": controls,
        "media": media,
        "stream": streams,
    }


def main() -> int:
    check = "--check" in sys.argv
    golden = build()
    if check:
        if not GOLDEN.exists():
            print(f"[vectors] 缺少 {GOLDEN}，先运行: python tools/gen-protocol/vectors.py")
            return 1
        current = json.loads(GOLDEN.read_text(encoding="utf-8"))
        if current == golden:
            print(f"[vectors] OK：{len(golden['control'])} 控制帧 + "
                  f"{len(golden['media'])} 媒体帧向量与脚本定义同步")
            return 0
        print("[vectors] FAIL：golden.json 与脚本定义不同步，重新生成提交：")
        print("          python tools/gen-protocol/vectors.py")
        return 1
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[vectors] 已生成 {GOLDEN}（{len(golden['control'])} 控制帧 + "
          f"{len(golden['media'])} 媒体帧 + {len(golden['stream'])} 混排流）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
