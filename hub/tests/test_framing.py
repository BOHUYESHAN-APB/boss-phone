"""hub 逻辑测试：帧编解码 / 流式分帧 / 握手（DESIGN_PROTOCOL §2/§4）。"""

import asyncio

from hub.core.eventbus import EventBus
from hub.core.session import DeviceRegistry
from hub.gateway.framing import FrameParser, encode_control, encode_media, make_envelope
from hub.gateway.handler import handle_control


def _hello(**over):
    p = {
        "proto": 1,
        "device": "passport:aa:bb",
        "fw": "0.1.0",
        "caps": ["voice.stt"],
        "resume_seq": 5,
    }
    p.update(over)
    return make_envelope("hello", "device", 0, p)


def test_mixed_stream_parse():
    """hello 控制帧 + voice 媒体帧 + 普通控制帧 混排解析。"""
    stream = (
        encode_control(_hello())
        + encode_media(1, 3, b"\x00" * 100)
        + encode_control(
            make_envelope("presence", "hub", 1, {"agent_id": "repo-b", "state": "running"})
        )
    )
    frames = FrameParser().feed(stream)
    assert frames[0][0] == "control" and frames[0][1]["payload"]["device"] == "passport:aa:bb"
    assert frames[1][0] == "media" and frames[1][1].type_name == "voice"
    assert len(frames[1][1].payload) == 100
    assert frames[2][0] == "control" and frames[2][1]["type"] == "presence"


def test_partial_chunk_accumulation():
    """半包分片：先喂一部分再喂剩余，应完整解析。"""
    stream = encode_control(_hello()) + encode_media(1, 3, b"\x00" * 10)
    p = FrameParser()
    assert p.feed(stream[:10]) == []
    out = p.feed(stream[10:])
    assert len(out) == 2 and out[0][0] == "control" and out[1][0] == "media"


def test_resync_on_garbage():
    """残渣字节应被丢弃并重同步到控制帧。"""
    p = FrameParser()
    out = p.feed(b"\x00\x01\x02" + encode_control(make_envelope("state", "hub", 1, {})))
    assert any(kind == "control" for kind, _ in out)


def test_hello_handshake_and_unauthenticated_block():
    """hello → 登记 + hello_ack；未握手控制帧按 4003 忽略。"""

    async def run() -> None:
        bus = EventBus()
        reg = DeviceRegistry()
        sent: list[dict] = []

        async def send(msg: dict) -> None:
            sent.append(msg)

        s = await handle_control(bus, reg, None, _hello(), link="cdc", send=send)
        assert s is not None and reg.active_count() == 1
        assert sent[0]["type"] == "hello_ack"
        assert sent[0]["payload"]["device_id"] == "passport:aa:bb"

        s2 = await handle_control(
            bus,
            reg,
            s,
            make_envelope("presence", "hub", 1, {"state": "running"}),
            link="cdc",
            send=send,
        )
        assert s2 is s

        s3 = await handle_control(
            bus, reg, None, make_envelope("state", "hub", 1, {}), link="ws", send=send
        )
        assert s3 is None  # 未握手 → 4003 拦截

    asyncio.run(run())
