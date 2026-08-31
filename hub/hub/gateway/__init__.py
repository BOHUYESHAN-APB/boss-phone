"""gateway 子包：CDC / WebSocket / 云中继隧道 三入口（DESIGN_HUB §1）。

各入口负责各自链路的分帧与收发，解析出的控制帧统一交给
`handler.handle_control` 生成同一 `DeviceSession` 并进事件总线。
"""
