"""Hub CLI（`python -m hub <子命令>`，DESIGN_HUB §8）。

子命令：
  serve       启动常驻进程（CDC/WS 双入口 + 心跳 + 遥测）
  link        显示设备会话 / seq / 链路
  telemetry   打印一次遥测快照
  sim         模拟板子脚本（虚拟 CDC，无板联调用）
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def _cmd_serve(args: argparse.Namespace) -> int:
    from hub.config import load_config
    from hub.server import run_server

    cfg = load_config(args.config)
    print(f"== BOSS PHONE Hub v{__import__('hub').__version__} (Python + asyncio) ==")
    print(f"serial: {cfg.serial.port or '(未配置，纯 WS 模式)'}")
    print(f"ws   : {cfg.ws.listen}  token: {'已设置' if cfg.ws.token else '未设置'}")
    try:
        asyncio.run(run_server(cfg))
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，退出。")
    return 0


def _cmd_link(args: argparse.Namespace) -> int:
    from hub.core.router import Route

    print("设备会话（M1 实装后从 sessions 读取；当前展示路由决策示意）")
    print(f"  示例路由: {Route.DIRECT}")
    return 0


def _cmd_telemetry(args: argparse.Namespace) -> int:
    from hub.telemetry import collect_snapshot

    snap = collect_snapshot()
    print(f"CPU {snap['cpu_percent']:.1f}% / 内存 {snap['mem_percent']:.1f}%")
    return 0


def _cmd_sim(args: argparse.Namespace) -> int:
    print("hub sim：虚拟 CDC 模拟板子（M1 联调工具，暂未实装）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hub", description="BOSS PHONE PC 总机房")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="启动常驻进程")
    s.add_argument("--config", default="hub.toml", help="配置文件路径（默认 hub.toml）")
    s.add_argument("--virtual-cdc", action="store_true", help="无板调试：虚拟串口")
    s.set_defaults(func=_cmd_serve)

    sub.add_parser("link", help="显示设备会话/seq/链路").set_defaults(func=_cmd_link)
    sub.add_parser("telemetry", help="打印遥测快照").set_defaults(func=_cmd_telemetry)
    sub.add_parser("sim", help="模拟板子（虚拟 CDC）").set_defaults(func=_cmd_sim)
    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 —— CLI 顶层兜底
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
