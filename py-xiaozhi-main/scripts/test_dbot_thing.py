#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D-BOT Thing 手动测试脚本.

用法（在项目根目录下执行）：
    PYTHONPATH=. python scripts/test_dbot_thing.py --ping
    PYTHONPATH=. python scripts/test_dbot_thing.py --descriptors
    PYTHONPATH=. python scripts/test_dbot_thing.py --states
    PYTHONPATH=. python scripts/test_dbot_thing.py --forward 20
    PYTHONPATH=. python scripts/test_dbot_thing.py --left 90
    PYTHONPATH=. python scripts/test_dbot_thing.py --stop
    PYTHONPATH=. python scripts/test_dbot_thing.py --set-ip 192.168.1.200
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 确保项目根目录在 sys.path 中（无论从哪里执行脚本）
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def setup_logging(verbose: bool = False):
    """配置日志输出。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def main():
    parser = argparse.ArgumentParser(
        description="D-BOT Thing 手动测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--descriptors", action="store_true", help="打印所有 Thing 描述符")
    parser.add_argument("--states", action="store_true", help="打印所有 Thing 当前状态")
    parser.add_argument("--ping", action="store_true", help="执行 Ping 检查在线状态")
    parser.add_argument("--move", type=float, metavar="CM", help="执行 Move(distance_cm)")
    parser.add_argument("--spin", type=float, metavar="DEG", help="执行 Spin(angle_deg)")
    parser.add_argument("--forward", type=float, metavar="CM", help="执行 MoveForward(distance_cm)")
    parser.add_argument("--backward", type=float, metavar="CM", help="执行 MoveBackward(distance_cm)")
    parser.add_argument("--left", type=float, metavar="DEG", help="执行 TurnLeft(angle_deg)")
    parser.add_argument("--right", type=float, metavar="DEG", help="执行 TurnRight(angle_deg)")
    parser.add_argument("--stop", action="store_true", help="执行 Stop")
    parser.add_argument("--set-ip", type=str, metavar="IP", help="执行 SetTargetIp(ip_address)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示调试日志")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("test_dbot")

    # 至少要指定一个操作
    has_action = any([
        args.descriptors, args.states, args.ping,
        args.move is not None, args.spin is not None,
        args.forward is not None, args.backward is not None,
        args.left is not None, args.right is not None,
        args.stop, args.set_ip,
    ])
    if not has_action:
        parser.print_help()
        print("\n错误：请至少指定一个操作，例如 --ping 或 --forward 20")
        sys.exit(1)

    # 初始化 ConfigManager（会自动加载 config/config.json）
    from src.utils.config_manager import ConfigManager

    config = ConfigManager.get_instance()

    # 读取并显示 DBOT 配置
    dbot_cfg = config.get_config("DBOT", {})
    logger.info(f"D-BOT 配置: IP={dbot_cfg.get('IP_ADDRESS')}, "
                f"Port={dbot_cfg.get('PORT')}, "
                f"LeftSpinPositive={dbot_cfg.get('LEFT_SPIN_POSITIVE')}")

    # 初始化 ThingManager 并注册设备
    from src.iot.thing_manager import ThingManager

    manager = ThingManager.get_instance()
    await manager.initialize_iot_devices(config)
    logger.info(f"已注册 Thing 数量: {len(manager.things)}")
    for t in manager.things:
        logger.info(f"  - {t.name}: {t.description}")

    # --descriptors: 打印描述符
    if args.descriptors:
        desc_json = await manager.get_descriptors_json()
        print("\n=== Thing Descriptors ===")
        print(json.dumps(json.loads(desc_json), ensure_ascii=False, indent=2))

    # --states: 打印状态
    if args.states:
        _changed, states_json = await manager.get_states_json(delta=False)
        print("\n=== Thing States ===")
        print(json.dumps(json.loads(states_json), ensure_ascii=False, indent=2))

    # 构建命令列表
    commands = []
    if args.ping:
        commands.append(("Ping", {"name": "DBot", "method": "Ping", "parameters": {}}))
    if args.move is not None:
        commands.append(("Move", {"name": "DBot", "method": "Move", "parameters": {"distance_cm": args.move}}))
    if args.spin is not None:
        commands.append(("Spin", {"name": "DBot", "method": "Spin", "parameters": {"angle_deg": args.spin}}))
    if args.forward is not None:
        commands.append(("MoveForward", {"name": "DBot", "method": "MoveForward", "parameters": {"distance_cm": args.forward}}))
    if args.backward is not None:
        commands.append(("MoveBackward", {"name": "DBot", "method": "MoveBackward", "parameters": {"distance_cm": args.backward}}))
    if args.left is not None:
        commands.append(("TurnLeft", {"name": "DBot", "method": "TurnLeft", "parameters": {"angle_deg": args.left}}))
    if args.right is not None:
        commands.append(("TurnRight", {"name": "DBot", "method": "TurnRight", "parameters": {"angle_deg": args.right}}))
    if args.stop:
        commands.append(("Stop", {"name": "DBot", "method": "Stop", "parameters": {}}))
    if args.set_ip:
        commands.append(("SetTargetIp", {"name": "DBot", "method": "SetTargetIp", "parameters": {"ip_address": args.set_ip}}))

    # 执行命令
    for label, command in commands:
        logger.info(f"执行: {label} -> {command['method']}({command.get('parameters', {})})")
        try:
            result = await manager.invoke(command)
            print(f"\n=== {label} 结果 ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"{label} 执行失败: {e}")
            print(f"\n=== {label} 错误 ===")
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False, indent=2))

    # 执行命令后刷新并打印最新状态
    if commands:
        _changed, states_json = await manager.get_states_json(delta=False)
        states = json.loads(states_json)
        dbot_state = next((s for s in states if s.get("name") == "DBot"), None)
        if dbot_state:
            print("\n=== D-BOT 最新状态 ===")
            print(json.dumps(dbot_state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
