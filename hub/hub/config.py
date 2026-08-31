"""配置加载：hub.toml（Python 3.11 标准库 tomllib，DESIGN_HUB §8）。

与 DESIGN_DEPLOYMENT 的示例 hub.toml 字段一一对应。
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SerialCfg:
    port: str = ""          # 板子 CDC1 串口；留空则纯 WS 模式
    baud: int = 115200      # CDC 虚拟串口波特率（可任意，常为 115200）


@dataclass
class WsCfg:
    listen: str = "0.0.0.0:8765"  # 局域网 WebSocket 入口
    token: str = "change-me"      # 设备/插件连接鉴权


@dataclass
class RelayCfg:                   # 阶段 3
    enabled: bool = False
    server: str = "wss://relay.example.com"
    token: str = ""


@dataclass
class OperatorCfg:
    provider: str = "openai"      # 或 deepseek/qwen...；多模态直听或两段式
    model: str = "gpt-4o-audio-preview"
    api_key: str = ""
    stt_engine: str = "windows"   # windows | whisper | cloud


@dataclass
class TelemetryCfg:
    interval_sec: int = 30
    github_token: str = ""
    budget_month: float = 500.0


@dataclass
class DictationCfg:                       # 语音输入法（DESIGN_OVERVIEW §8.6）
    inject: str = "auto"                 # type | paste | auto（文字落到光标处）
    paste_threshold: int = 200           # auto：超过该长度走剪贴板粘贴
    correct: bool = True                 # 词表纠错层开关（度量收益用）
    terms_file: str = ""                 # 用户词表 JSON（热更新，不烧固件）
    hotwords: str = ""                   # 热词（逗号分隔，注入 STT initial_prompt）


@dataclass
class HubConfig:
    serial: SerialCfg = field(default_factory=SerialCfg)
    ws: WsCfg = field(default_factory=WsCfg)
    relay: RelayCfg = field(default_factory=RelayCfg)
    operator: OperatorCfg = field(default_factory=OperatorCfg)
    telemetry: TelemetryCfg = field(default_factory=TelemetryCfg)
    dictation: DictationCfg = field(default_factory=DictationCfg)


def load_config(path: str | Path) -> HubConfig:
    p = Path(path)
    if not p.exists():
        return HubConfig()  # 缺省配置，serve 以纯 WS 模式启动
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    return HubConfig(
        serial=SerialCfg(**raw.get("serial", {})),
        ws=WsCfg(**raw.get("ws", {})),
        relay=RelayCfg(**raw.get("relay", {})),
        operator=OperatorCfg(**raw.get("operator", {})),
        telemetry=TelemetryCfg(**raw.get("telemetry", {})),
        dictation=DictationCfg(**raw.get("dictation", {})),
    )
