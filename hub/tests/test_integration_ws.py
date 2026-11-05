"""L3 Hub 集成测试（DESIGN_TEST）：起真 WS 网关，虚拟设备全链路。

与 test_framing 的函数级测试不同：这里启动真实的 ws_listener（含
handle_control 分发 / DeviceRegistry 登记 / EventBus 事件 / 断连清理），
用 websockets 客户端模拟设备，验证"模块拼起来能跑"：
  hello → hello_ack → state 分发 → 媒体帧不干扰 → 断连清理（device.left）
未握手拦截（4003）在 WS 链路上同样生效。
"""

import asyncio
import json
import socket

import websockets

from hub.config import HubConfig, WsCfg
from hub.core.eventbus import EventBus
from hub.core.session import DeviceRegistry
from hub.gateway.framing import encode_media
from hub.gateway.ws import ws_listener


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _start_hub():
    bus = EventBus()
    registry = DeviceRegistry()
    port = _free_port()
    cfg = HubConfig(ws=WsCfg(listen=f"127.0.0.1:{port}"))
    server = asyncio.create_task(ws_listener(cfg, bus, registry))
    # 轮询等监听就绪（固定 sleep 在 CI 上不可靠）
    deadline = asyncio.get_event_loop().time() + 5
    while True:
        try:
            _ = await websockets.connect(f"ws://127.0.0.1:{port}", close_timeout=0.1)
            break
        except OSError as exc:
            if asyncio.get_event_loop().time() > deadline:
                raise AssertionError("WS 网关 5s 内未就绪") from exc
            await asyncio.sleep(0.05)
    return bus, registry, port, server


def _hello(device: str = "passport:AA:BB:CC:DD:EE:FF") -> str:
    return json.dumps(
        {
            "type": "hello",
            "from": "device",
            "to": "hub",
            "seq": 1,
            "ts": 1756000000000,
            "payload": {"proto": 1, "device": device, "fw": "0.1.0", "caps": ["voice.stt"]},
        },
        ensure_ascii=False,
    )


def test_ws_full_device_lifecycle():
    asyncio.run(_lifecycle())


async def _lifecycle():
    bus, registry, port, server = await _start_hub()
    q_hello = bus.subscribe("device.hello")
    q_ctrl = bus.subscribe("device.control")
    q_left = bus.subscribe("device.left")
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            # 1) hello → hello_ack（协商版本/能力/校时）
            await ws.send(_hello())
            ack = json.loads(await asyncio.wait_for(ws.recv(), 5))
            assert ack["type"] == "hello_ack"
            assert ack["payload"]["proto"] == 1
            assert ack["payload"]["device_id"] == "passport:AA:BB:CC:DD:EE:FF"
            assert registry.active_count() == 1

            # 2) 握手后 state 控制帧 → 事件总线 device.control
            await ws.send(
                json.dumps(
                    {
                        "type": "state",
                        "from": "device",
                        "to": "hub",
                        "seq": 2,
                        "ts": 1756000000001,
                        "payload": {},
                    }
                )
            )
            ev = await asyncio.wait_for(q_ctrl.get(), 5)
            assert ev["type"] == "state"
            assert ev["device_id"] == "passport:AA:BB:CC:DD:EE:FF"

            # 3) 二进制媒体帧（voice 直连通道，M2 只计数）不破坏会话
            await ws.send(encode_media(1, 3, b"\x00" * 64))
            await asyncio.sleep(0.1)
            assert registry.active_count() == 1

        # 4) 断开连接 → 会话清理 + device.left
        left = await asyncio.wait_for(q_left.get(), 5)
        assert left["reason"] == "ws-closed"
        assert registry.active_count() == 0

        # hello 事件也已广播（入网可见）
        hello_ev = await asyncio.wait_for(q_hello.get(), 1)
        assert hello_ev["device_id"] == "passport:AA:BB:CC:DD:EE:FF"
        assert hello_ev["link"] == "ws"
    finally:
        server.cancel()
        try:
            await server
        except asyncio.CancelledError:
            pass


def test_ws_unauthenticated_control_blocked():
    """未握手控制帧：无 hello_ack 回复、不进事件总线、不登记会话（4003）。"""
    asyncio.run(_unauth())


async def _unauth():
    bus, registry, port, server = await _start_hub()
    q_ctrl = bus.subscribe("device.control")
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "state",
                        "from": "device",
                        "to": "hub",
                        "seq": 1,
                        "ts": 1756000000000,
                        "payload": {},
                    }
                )
            )
            # 唯一合法回复是 hello_ack；未握手不会有任何回帧
            try:
                msg = await asyncio.wait_for(ws.recv(), 0.5)
                raise AssertionError(f"未握手不应有回复，却收到: {msg}")
            except TimeoutError:
                pass
        assert registry.active_count() == 0
        assert q_ctrl.empty()
    finally:
        server.cancel()
        try:
            await server
        except asyncio.CancelledError:
            pass
