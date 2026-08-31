"""BOSS PHONE PC 总机房（Hub）。

Python + asyncio 常驻单进程：接收多端连接（USB CDC / WebSocket / 云中继隧道）、
维护设备会话、路由决策、转发 Agent 事件、聚合遥测、调度接线员（DESIGN_HUB.md）。

M0 范围：asyncio 骨架 + STT 引擎（windows / whisper / cloud）+ hub-lite 验证 CLI。
M1 范围：gateway（CDC/WS 双入口）+ core（会话/路由/事件总线）+ agents + telemetry。
"""

__version__ = "0.1.0"
