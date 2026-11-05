"""CDC 入口（DESIGN_HUB §1 gateway）：pyserial 监听板子 CDC1 串口。

字节流 → FrameParser 分帧 → 统一 handle_control 分发；媒体帧只计数不进场。
`cfg.serial.port == "virtual"` 走 pyserial loop:// 虚拟串口，供无板调试（风险 H1）。
"""

from __future__ import annotations

import asyncio

import serial

from hub.config import HubConfig
from hub.core.eventbus import EventBus
from hub.core.session import DeviceRegistry, DeviceSession
from hub.gateway.framing import FrameParser, encode_control
from hub.gateway.handler import handle_control

READ_CHUNK = 4096


async def cdc_listener(cfg: HubConfig, bus: EventBus, registry: DeviceRegistry) -> None:
    port = cfg.serial.port
    while True:
        try:
            if port == "virtual":
                ser = serial.serial_for_url("loop://", baudrate=cfg.serial.baud, timeout=0.1)
                print("[cdc] 虚拟串口（loop://）——无板调试模式")
            else:
                ser = serial.Serial(port, cfg.serial.baud, timeout=0.1)
                print(f"[cdc] 串口已打开: {port} @ {cfg.serial.baud}")
        except serial.SerialException as exc:
            print(f"[cdc] 打开 {port} 失败: {exc}（H1：检查是否被 VS Code 串口监视器占用）")
            await asyncio.sleep(5)
            continue

        parser = FrameParser()
        session: DeviceSession | None = None
        media_count = 0
        try:
            while True:
                # 阻塞读放线程，避免卡事件循环（timeout=0.1s，无数据返回 b''）
                data = await asyncio.to_thread(ser.read, READ_CHUNK)
                if not data:
                    await asyncio.sleep(0.02)
                    continue
                for kind, obj in parser.feed(data):
                    if kind == "error":
                        print(f"[cdc] 帧解析丢弃: {obj}")
                    elif kind == "control":
                        session = await handle_control(
                            bus, registry, session, obj, link="cdc", send=_make_send(ser)
                        )
                    else:
                        # 媒体帧走直连通道，M2 实装；骨架阶段只计数
                        media_count += 1
                        if media_count == 1:
                            print("[cdc] 收到媒体帧（voice/audio 直连通道 M2 实装）")
        except (serial.SerialException, OSError):
            print(f"[cdc] 链路断开: {port}，等待重连…")
        except asyncio.CancelledError:
            raise
        finally:
            if session is not None and registry.get(session.device_id) is session:
                registry.remove(session.device_id)
                await bus.publish(
                    "device.left", {"device_id": session.device_id, "reason": "cdc-closed"}
                )
            ser.close()
        await asyncio.sleep(2)


def _make_send(ser: serial.Serial):
    async def send(msg: dict) -> None:
        await asyncio.to_thread(ser.write, encode_control(msg))

    return send
