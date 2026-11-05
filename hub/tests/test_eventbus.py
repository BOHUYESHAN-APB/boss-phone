"""L1 单元测试：EventBus pub/sub（DESIGN_HUB §1）。"""

import asyncio

from hub.core.eventbus import EventBus


def test_publish_without_subscribers_is_noop():
    async def run() -> None:
        await EventBus().publish("device.hello", {"x": 1})  # 不应抛错

    asyncio.run(run())


def test_subscribe_receive_in_order():
    async def run() -> None:
        bus = EventBus()
        q = bus.subscribe("device.control")
        for i in range(3):
            await bus.publish("device.control", {"seq": i})
        assert [q.get_nowait()["seq"] for _ in range(3)] == [0, 1, 2]

    asyncio.run(run())


def test_multiple_subscribers_all_receive():
    async def run() -> None:
        bus = EventBus()
        q1, q2 = bus.subscribe("device.hello"), bus.subscribe("device.hello")
        await bus.publish("device.hello", {"device_id": "d1"})
        assert q1.get_nowait() == {"device_id": "d1"}
        assert q2.get_nowait() == {"device_id": "d1"}

    asyncio.run(run())


def test_topic_isolation_and_unsubscribe():
    async def run() -> None:
        bus = EventBus()
        q = bus.subscribe("device.left")
        other = bus.subscribe("device.hello")
        await bus.publish("device.hello", {"n": 1})
        assert other.get_nowait() == {"n": 1}
        assert q.empty()  # 主题隔离

        bus.unsubscribe("device.hello", other)
        await bus.publish("device.hello", {"n": 2})
        assert other.empty()  # 退订后不再收

    asyncio.run(run())
