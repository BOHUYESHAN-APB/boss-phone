"""DeviceSession：统一会话抽象 + 注册表（DESIGN_HUB §1/§3）。

CDC/WS/中继隧道各自解析帧后，在此登记为同一 `DeviceSession`，
供 core/router 心跳判定与路由决策使用。媒体流量不走这里（直连通道）。
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

# 心跳：设备 10s 一个 ping；Hub 30s 巡检，连续 2 次超时判失联 → stale 阈值 60s
HEARTBEAT_PING_S = 10
HEARTBEAT_PATROL_S = 30
STALE_AFTER_S = HEARTBEAT_PATROL_S * 2


@dataclass
class DeviceSession:
    device_id: str
    link: str  # cdc | ws
    caps: list[str]
    fw: str
    resume_seq: int | None = None  # 断线补收游标（DESIGN_PROTOCOL §4.2）
    seq_out: int = 1  # Hub → 本设备 的出站 seq（每设备独立）
    last_seen: float = field(default_factory=time.monotonic)
    send: Callable[[dict], Awaitable[None]] | None = None  # 网关注入的发送器

    def touch(self) -> None:
        self.last_seen = time.monotonic()

    def next_seq(self) -> int:
        seq = self.seq_out
        self.seq_out += 1
        return seq

    def is_stale(self, now: float | None = None) -> bool:
        return (now or time.monotonic()) - self.last_seen > STALE_AFTER_S


class DeviceRegistry:
    """按 device_id 索引活跃会话；同一设备新链路登记时顶掉旧会话。"""

    def __init__(self) -> None:
        self._sessions: dict[str, DeviceSession] = {}

    def add(self, session: DeviceSession) -> None:
        self._sessions[session.device_id] = session

    def get(self, device_id: str) -> DeviceSession | None:
        return self._sessions.get(device_id)

    def remove(self, device_id: str) -> None:
        self._sessions.pop(device_id, None)

    def active_count(self) -> int:
        return len(self._sessions)

    def stale(self, now: float | None = None) -> list[DeviceSession]:
        t = now or time.monotonic()
        return [s for s in self._sessions.values() if s.is_stale(t)]
