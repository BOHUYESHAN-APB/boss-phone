"""网关统一消息分发：CDC/WS 共用（DESIGN_PROTOCOL §2 信封）。

- `hello` → 登记 DeviceSession + 回 hello_ack（协商版本/能力/校时）
- 其余控制帧 → event bus `device.control`
- 媒体帧不进事件总线（直连通道），由各入口自行计数
"""

from __future__ import annotations

import time
from typing import Awaitable, Callable, Optional

from hub.core.eventbus import EventBus
from hub.core.session import DeviceSession, DeviceRegistry
from hub.gateway.framing import make_envelope

PROTO_VERSION = 1
# 服务端能力集（DESIGN_PROTOCOL §5 词汇表；M1 骨架先声明核心几项）
SERVER_CAPS = ["voice.stt", "state.push", "ring", "memo"]


async def handle_control(
    bus: EventBus,
    registry: DeviceRegistry,
    session: Optional[DeviceSession],
    msg: dict,
    *,
    link: str,
    send: Callable[[dict], Awaitable[None]],
) -> Optional[DeviceSession]:
    """处理一条控制帧，返回更新后的会话（hello 后为新会话，未握手则 None）。"""
    mtype = msg.get("type")
    if mtype == "hello":
        payload = msg.get("payload") or {}  # 消息字段都在信封 payload 内（§3.1）
        device_id = payload.get("device", "")
        if not device_id:
            print(f"[{link}] hello 缺少 device 字段，忽略")
            return session
        new_session = DeviceSession(
            device_id=device_id,
            link=link,
            caps=list(payload.get("caps", [])),
            fw=payload.get("fw", ""),
            resume_seq=payload.get("resume_seq"),
            send=send,
        )
        registry.add(new_session)
        ack = make_envelope(
            "hello_ack",
            device_id,
            new_session.next_seq(),
            {
                "proto": min(int(payload.get("proto", 1)), PROTO_VERSION),
                "caps": SERVER_CAPS,
                "device_id": device_id,
                "server_time": int(time.time() * 1000),
            },
        )
        await send(ack)
        await bus.publish(
            "device.hello",
            {
                "device_id": device_id,
                "link": link,
                "caps": new_session.caps,
                "fw": new_session.fw,
            },
        )
        print(f"[{link}] 设备入网: {device_id}（fw={new_session.fw} caps={new_session.caps}）")
        return new_session

    # 非 hello：必须先握手（错误码 4003）
    if session is None:
        print(f"[{link}] 收到 {mtype} 但未握手（4003），忽略")
        return None

    session.touch()
    await bus.publish(
        "device.control",
        {"device_id": session.device_id, "type": mtype, "envelope": msg},
    )
    return session
