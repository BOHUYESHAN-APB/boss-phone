"""事件总线（DESIGN_HUB §1/§2）：全内部分发（asyncio）。

低开销 pub/sub：订阅者按主题收事件；消息顺序保证（按 from seq）由
core/router 在发布前负责，本总线只做广播。媒体流量不进事件总线（走直连通道）。
"""

from __future__ import annotations

import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, topic: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs[topic].add(q)
        return q

    def unsubscribe(self, topic: str, q: asyncio.Queue) -> None:
        self._subs[topic].discard(q)

    async def publish(self, topic: str, event: object) -> None:
        """广播到该主题全部订阅者（无订阅者则丢弃，不阻塞）。"""
        for q in list(self._subs.get(topic, ())):
            await q.put(event)
