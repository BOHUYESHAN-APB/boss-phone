"""遥测聚合（DESIGN_HUB §6）：PC CPU/内存快照（psutil）。"""

from __future__ import annotations

import psutil


def collect_snapshot() -> dict:
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "mem_percent": psutil.virtual_memory().percent,
    }
