"""WebSocket 入口（DESIGN_HUB §1 gateway）：局域网 WS，设备/手机/插件接入。

控制帧用 text（JSON），媒体帧用 binary；字段与 CDC 同源（DESIGN_PROTOCOL §4.1）。
WS 天然按消息分帧，无需 FrameParser。
"""

from __future__ import annotations

import asyncio
import json
from functools import partial

import websockets

from hub.config import HubConfig
from hub.core.eventbus import EventBus
from hub.core.session import DeviceRegistry, DeviceSession
from hub.gateway.handler import handle_control


async def ws_listener(cfg: HubConfig, bus: EventBus, registry: DeviceRegistry) -> None:
    host, _, port_s = cfg.ws.listen.rpartition(":")
    port = int(port_s)
    handler = partial(_ws_handler, bus=bus, registry=registry)
    # ping_interval 20s：WS 层心跳，设备侧 10s ping 为业务层（§3）
    async with websockets.serve(handler, host, port, ping_interval=20, ping_timeout=10):
        print(f"[ws] WebSocket 监听: ws://{cfg.ws.listen}")
        await asyncio.Future()  # 常驻


async def _ws_handler(websocket, bus: EventBus, registry: DeviceRegistry) -> None:
    session: DeviceSession | None = None
    media_count = 0
    try:
        async for raw in websocket:
            if isinstance(raw, str):
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                session = await handle_control(
                    bus, registry, session, msg, link="ws", send=_ws_send(websocket)
                )
            else:
                # binary 媒体帧：直连通道 M2 实装，骨架阶段只计数
                media_count += 1
                if media_count == 1:
                    print("[ws] 收到媒体帧（voice/audio 直连通道 M2 实装）")
    finally:
        if session is not None and registry.get(session.device_id) is session:
            registry.remove(session.device_id)
            await bus.publish(
                "device.left", {"device_id": session.device_id, "reason": "ws-closed"}
            )


def _ws_send(websocket):
    async def send(msg: dict) -> None:
        await websocket.send(json.dumps(msg, ensure_ascii=False))

    return send
