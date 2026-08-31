"""asyncio 常驻进程骨架（DESIGN_HUB §2 进程模型）。

M0 骨架：加载配置 → 心跳巡检 + 遥测周期任务常驻；
CDC/WS 接入（M1）在此挂接 gateway 监听任务。CPU 密集工作（whisper 推理）
放 asyncio.to_thread / 进程池，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio

from hub.config import HubConfig
from hub.core.eventbus import EventBus
from hub.core.session import DeviceRegistry


async def run_server(cfg: HubConfig) -> None:
    bus = EventBus()
    registry = DeviceRegistry()
    tasks: list[asyncio.Task] = []

    if cfg.serial.port:
        from hub.gateway.cdc import cdc_listener

        tasks.append(asyncio.create_task(cdc_listener(cfg, bus, registry), name="cdc"))
        print(f"[gateway] CDC 监听启动: {cfg.serial.port} @ {cfg.serial.baud}")

    if cfg.ws.listen:
        from hub.gateway.ws import ws_listener

        tasks.append(asyncio.create_task(ws_listener(cfg, bus, registry), name="ws"))
        print(f"[gateway] WS 监听启动: {cfg.ws.listen}")

    async def heartbeat_loop() -> None:
        # 30s 巡检，连续 2 次超时（60s）判失联（DESIGN_HUB §3）
        while True:
            await asyncio.sleep(30)
            for s in registry.stale():
                print(f"[heartbeat] 设备失联: {s.device_id} link={s.link}")
                registry.remove(s.device_id)
                await bus.publish("device.left", {"device_id": s.device_id, "reason": "heartbeat-timeout"})
            print(f"[heartbeat] 巡检: 活跃会话 {registry.active_count()}")

    tasks.append(asyncio.create_task(heartbeat_loop(), name="heartbeat"))

    print("[hub] 就绪。Ctrl+C 退出。")
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.cancel()
