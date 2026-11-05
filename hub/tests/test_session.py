"""L1 单元测试：DeviceSession / DeviceRegistry（DESIGN_HUB §3 心跳语义）。"""

import asyncio
import time

from hub.core.eventbus import EventBus
from hub.core.session import STALE_AFTER_S, DeviceRegistry, DeviceSession


def _session(device_id: str = "passport:AA:BB") -> DeviceSession:
    return DeviceSession(device_id=device_id, link="ws", caps=["voice.stt"], fw="0.1.0")


def test_next_seq_increments_from_one():
    s = _session()
    assert [s.next_seq() for _ in range(3)] == [1, 2, 3]


def test_is_stale_threshold():
    """失联阈值 STALE_AFTER_S（60s）：边界不 stale，超过才 stale。"""
    s = _session()
    assert not s.is_stale(s.last_seen + STALE_AFTER_S)  # 恰好 60s：仍在
    assert s.is_stale(s.last_seen + STALE_AFTER_S + 0.01)  # 超过：失联
    assert not s.is_stale()  # 刚建：活跃


def test_touch_refreshes_last_seen():
    s = _session()
    now = time.monotonic()
    s.last_seen = now - STALE_AFTER_S - 1
    assert s.is_stale(now)  # 已老化
    s.touch()
    assert not s.is_stale()


def test_registry_add_get_remove():
    reg = DeviceRegistry()
    s = _session()
    reg.add(s)
    assert reg.get("passport:AA:BB") is s
    assert reg.active_count() == 1
    reg.remove("passport:AA:BB")
    assert reg.get("passport:AA:BB") is None
    assert reg.active_count() == 0
    reg.remove("不存在的 id")  # 幂等


def test_registry_new_link_replaces_old_session():
    """同一设备重连（新链路）应顶掉旧会话。"""
    reg = DeviceRegistry()
    old = _session()
    reg.add(old)
    new = _session()  # 同 device_id
    reg.add(new)
    assert reg.get("passport:AA:BB") is new
    assert reg.active_count() == 1


def test_registry_stale_filter():
    reg = DeviceRegistry()
    fresh, stale = _session("passport:01"), _session("passport:02")
    stale.last_seen -= STALE_AFTER_S + 10
    reg.add(fresh)
    reg.add(stale)
    assert [s.device_id for s in reg.stale()] == ["passport:02"]


def test_heartbeat_patrol_semantics():
    """心跳巡检组合语义（server.heartbeat_loop 的核心）：stale → remove → device.left。"""

    async def run() -> None:
        bus = EventBus()
        q = bus.subscribe("device.left")
        reg = DeviceRegistry()
        stale = _session("passport:09")
        stale.last_seen -= STALE_AFTER_S + 1
        reg.add(stale)

        for s in reg.stale():  # 与 heartbeat_loop 相同的清理逻辑
            reg.remove(s.device_id)
            await bus.publish(
                "device.left", {"device_id": s.device_id, "reason": "heartbeat-timeout"}
            )

        assert reg.active_count() == 0
        ev = await asyncio.wait_for(q.get(), 1)
        assert ev == {"device_id": "passport:09", "reason": "heartbeat-timeout"}

    asyncio.run(run())
