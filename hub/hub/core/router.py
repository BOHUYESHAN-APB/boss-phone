"""路由决策（DESIGN_HUB §3）：DIRECT / RELAY / OFFLINE。

纯函数：给定目标设备会话状态与中继配置，返回路由。M1 由 DeviceSession
维护活跃会话数并在此决策。
"""

from __future__ import annotations

from enum import Enum


class Route(str, Enum):
    DIRECT = "direct"    # 目标设备有活跃会话 → 直发（零公网暴露）
    RELAY = "relay"      # 全失活 + 中继开启 → 云中继推送唤醒
    OFFLINE = "offline"  # 全失活 + 中继关闭 → 写离线队列，等回连补发


def decide_route(*, active_sessions: int, relay_enabled: bool) -> Route:
    """路由决策表（DESIGN_HUB §3）：

    | 设备会话状态          | 行为          |
    |----------------------|--------------|
    | 有活跃会话（USB 优先）| DIRECT 直发    |
    | 全部失活 + 中继开启    | RELAY         |
    | 全部失活 + 中继关闭    | OFFLINE       |
    """
    if active_sessions > 0:
        return Route.DIRECT
    return Route.RELAY if relay_enabled else Route.OFFLINE
