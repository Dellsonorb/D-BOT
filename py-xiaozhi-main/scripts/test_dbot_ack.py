#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D-BOT ACK 回执测试脚本.

用法（在项目根目录下执行）：
    PYTHONPATH=. python scripts/test_dbot_ack.py --move 10
    PYTHONPATH=. python scripts/test_dbot_ack.py --spin -90
    PYTHONPATH=. python scripts/test_dbot_ack.py --stop
    PYTHONPATH=. python scripts/test_dbot_ack.py --emergency-stop
    PYTHONPATH=. python scripts/test_dbot_ack.py --sequence
    PYTHONPATH=. python scripts/test_dbot_ack.py --square
    PYTHONPATH=. python scripts/test_dbot_ack.py --demo
    PYTHONPATH=. python scripts/test_dbot_ack.py --go-forward
    PYTHONPATH=. python scripts/test_dbot_ack.py --go-backward
    PYTHONPATH=. python scripts/test_dbot_ack.py --turn-left
    PYTHONPATH=. python scripts/test_dbot_ack.py --turn-right
    PYTHONPATH=. python scripts/test_dbot_ack.py --turn-around
    PYTHONPATH=. python scripts/test_dbot_ack.py --perform-demo
    PYTHONPATH=. python scripts/test_dbot_ack.py --descriptors
    PYTHONPATH=. python scripts/test_dbot_ack.py --states
    PYTHONPATH=. python scripts/test_dbot_ack.py --ping
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 确保项目根目录在 sys.path 中
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
        description="D-BOT ACK 回执测试",
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
    parser.add_argument("--emergency-stop", action="store_true", help="执行 EmergencyStop")
    parser.add_argument("--sequence", action="store_true", help="执行预设动作序列")
    parser.add_argument("--square", action="store_true", help="执行 SquarePatrol（走正方形）")
    parser.add_argument("--demo", action="store_true", help="执行 DemoDance（演示动作）")
    parser.add_argument("--go-forward", action="store_true", help="执行 GoForwardALittle")
    parser.add_argument("--go-backward", action="store_true", help="执行 GoBackwardALittle")
    parser.add_argument("--turn-left", action="store_true", help="执行 TurnLeftALittle")
    parser.add_argument("--turn-right", action="store_true", help="执行 TurnRightALittle")
    parser.add_argument("--turn-around", action="store_true", help="执行 TurnAround（掉头）")
    parser.add_argument("--perform-demo", action="store_true", help="执行 PerformDemo")
    parser.add_argument("--set-ip", type=str, metavar="IP", help="执行 SetTargetIp(ip_address)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示调试日志")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("test_dbot_ack")

    # 至少要指定一个操作
    has_action = any([
        args.descriptors, args.states, args.ping,
        args.move is not None, args.spin is not None,
        args.forward is not None, args.backward is not None,
        args.left is not None, args.right is not None,
        args.stop, args.emergency_stop,
        args.sequence, args.square, args.demo,
        args.go_forward, args.go_backward,
        args.turn_left, args.turn_right, args.turn_around,
        args.perform_demo,
        args.set_ip,
    ])
    if not has_action:
        parser.print_help()
        print("\n错误：请至少指定一个操作，例如 --ping 或 --move 10")
        sys.exit(1)

    # 初始化 ConfigManager
    from src.utils.config_manager import ConfigManager

    config = ConfigManager.get_instance()

    # 读取并显示 DBOT 配置
    dbot_cfg = config.get_config("DBOT", {})
    logger.info(
        "D-BOT 配置: IP=%s, Port=%s, LeftSpinPositive=%s, ExpectAck=%s, AckTimeout=%s",
        dbot_cfg.get("IP_ADDRESS"),
        dbot_cfg.get("PORT"),
        dbot_cfg.get("LEFT_SPIN_POSITIVE"),
        dbot_cfg.get("EXPECT_ACK"),
        dbot_cfg.get("ACK_TIMEOUT_SEC"),
    )

    # 初始化 ThingManager 并注册设备
    from src.iot.thing_manager import ThingManager

    manager = ThingManager.get_instance()
    await manager.initialize_iot_devices(config)
    logger.info("已注册 Thing 数量: %d", len(manager.things))
    for t in manager.things:
        logger.info("  - %s: %s", t.name, t.description)

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
    if args.emergency_stop:
        commands.append(("EmergencyStop", {"name": "DBot", "method": "EmergencyStop", "parameters": {}}))
    if args.sequence:
        sequence = [
            {"method": "MoveForward", "parameters": {"distance_cm": 10}},
            {"method": "TurnLeft", "parameters": {"angle_deg": 90}},
            {"method": "MoveForward", "parameters": {"distance_cm": 10}},
            {"method": "TurnRight", "parameters": {"angle_deg": 90}},
        ]
        commands.append(("RunSequence", {"name": "DBot", "method": "RunSequence", "parameters": {"sequence": json.dumps(sequence, ensure_ascii=False)}}))
    if args.square:
        commands.append(("SquarePatrol", {"name": "DBot", "method": "SquarePatrol", "parameters": {"side_cm": 20, "turn_deg": 90}}))
    if args.demo:
        commands.append(("DemoDance", {"name": "DBot", "method": "DemoDance", "parameters": {}}))
    if args.go_forward:
        commands.append(("GoForwardALittle", {"name": "DBot", "method": "GoForwardALittle", "parameters": {}}))
    if args.go_backward:
        commands.append(("GoBackwardALittle", {"name": "DBot", "method": "GoBackwardALittle", "parameters": {}}))
    if args.turn_left:
        commands.append(("TurnLeftALittle", {"name": "DBot", "method": "TurnLeftALittle", "parameters": {}}))
    if args.turn_right:
        commands.append(("TurnRightALittle", {"name": "DBot", "method": "TurnRightALittle", "parameters": {}}))
    if args.turn_around:
        commands.append(("TurnAround", {"name": "DBot", "method": "TurnAround", "parameters": {}}))
    if args.perform_demo:
        commands.append(("PerformDemo", {"name": "DBot", "method": "PerformDemo", "parameters": {}}))
    if args.set_ip:
        commands.append(("SetTargetIp", {"name": "DBot", "method": "SetTargetIp", "parameters": {"ip_address": args.set_ip}}))

    # 执行命令
    for label, command in commands:
        logger.info("执行: %s -> %s(%s)", label, command['method'], command.get('parameters', {}))
        try:
            result = await manager.invoke(command)
            print(f"\n=== {label} 结果 ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # 如果有 ACK 信息，额外打印
            if isinstance(result, dict) and "cmd_id" in result:
                print(f"  cmd_id: {result.get('cmd_id')}")
                print(f"  stage:  {result.get('stage', 'N/A')}")
                print(f"  status: {result.get('status', 'N/A')}")

        except Exception as e:
            logger.error("%s 执行失败: %s", label, e)
            print(f"\n=== {label} 错误 ===")
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False, indent=2))

    # 执行命令后刷新并打印最新状态
    if commands:
        _changed, states_json = await manager.get_states_json(delta=False)
        states = json.loads(states_json)
        dbot_state = next((s for s in states if s.get("name") == "DBot"), None)
        if dbot_state:
            state = dbot_state.get("state", {})
            print("\n=== D-BOT 最新状态 ===")
            print(f"  机器人状态: {state.get('robot_status')}")
            print(f"  最近动作:   {state.get('last_action')}")
            print(f"  最近结果:   {state.get('last_result')}")
            print(f"  最近错误:   {state.get('last_error')}")
            print(f"  ACK 启用:   {state.get('ack_enabled')}")
            print(f"  命令 ID:    {state.get('last_command_id')}")
            print(f"  ACK 阶段:   {state.get('last_ack_stage')}")
            print(f"  ACK 信息:   {state.get('last_ack_message')}")
            print(f"  ACK 时间:   {state.get('last_ack_time')}")


if __name__ == "__main__":
    asyncio.run(main())
