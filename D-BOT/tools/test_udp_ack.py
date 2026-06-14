#!/usr/bin/env python3
"""
D-BOT UDP 控制命令测试脚本
测试 STOP / EMERGENCY_STOP / ACK 回执功能

用法:
  python3 tools/test_udp_ack.py <D-BOT的IP地址>

依赖: pip3 install (无额外依赖，仅标准库)
"""

import socket
import json
import time
import uuid
import sys

# ─── 配置 ───────────────────────────────────────────────
UDP_PORT = 6090
RECV_TIMEOUT = 2.0   # 等待 ACK 的超时秒数
# ─────────────────────────────────────────────────────────


def make_sock():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(RECV_TIMEOUT)
    return sock


def send_and_recv(sock, addr, msg):
    """发送一条 JSON 命令，收集所有返回的 ACK 直到超时"""
    data = json.dumps(msg).encode()
    sock.sendto(data, addr)
    print(f"  >>> {json.dumps(msg, ensure_ascii=False)}")

    acks = []
    while True:
        try:
            resp, _ = sock.recvfrom(4096)
            decoded = resp.decode()
            print(f"  <<< {decoded}")
            acks.append(json.loads(decoded))
        except socket.timeout:
            break
    return acks


def check_ack(acks, expected_stage, expected_status="success"):
    """检查 ACK 列表中是否包含预期的 stage"""
    for ack in acks:
        if ack.get("stage") == expected_stage and ack.get("status") == expected_status:
            return True
    return False


def cmd_id():
    return str(uuid.uuid4())[:8]


# ─── 测试用例 ────────────────────────────────────────────

def test_move_with_ack(sock, addr):
    """测试 1: MOVE 带 ACK → 期望 received + started + completed"""
    print("\n[测试1] MOVE 带 ACK (target=10.0)")
    cid = cmd_id()
    acks = send_and_recv(sock, addr, {
        "cmd_id": cid,
        "action": "MOVE",
        "target": 10.0,
        "expect_ack": True,
    })
    # 等命令执行完成后再收一次
    time.sleep(4)
    try:
        while True:
            resp, _ = sock.recvfrom(4096)
            decoded = resp.decode()
            print(f"  <<< {decoded}")
            acks.append(json.loads(decoded))
    except socket.timeout:
        pass

    ok = (check_ack(acks, "received") and
          check_ack(acks, "started") and
          check_ack(acks, "completed"))
    print(f"  结果: {'✅ 通过' if ok else '❌ 失败'} (收到 {len(acks)} 条 ACK)")
    return ok


def test_spin_with_ack(sock, addr):
    """测试 2: SPIN 带 ACK → 期望 received + started + completed"""
    print("\n[测试2] SPIN 带 ACK (target=45)")
    cid = cmd_id()
    acks = send_and_recv(sock, addr, {
        "cmd_id": cid,
        "action": "SPIN",
        "target": 45.0,
        "expect_ack": True,
    })
    time.sleep(4)
    try:
        while True:
            resp, _ = sock.recvfrom(4096)
            decoded = resp.decode()
            print(f"  <<< {decoded}")
            acks.append(json.loads(decoded))
    except socket.timeout:
        pass

    ok = (check_ack(acks, "received") and
          check_ack(acks, "started") and
          check_ack(acks, "completed"))
    print(f"  结果: {'✅ 通过' if ok else '❌ 失败'} (收到 {len(acks)} 条 ACK)")
    return ok


def test_stop_with_ack(sock, addr):
    """测试 3: 发送 MOVE，1秒后发送 STOP → 期望 STOP 的 received + completed"""
    print("\n[测试3] STOP 中断 MOVE (带 ACK)")

    # 先发一个长距离 MOVE
    print("  -- 发送 MOVE(50) --")
    send_and_recv(sock, addr, {
        "cmd_id": cmd_id(),
        "action": "MOVE",
        "target": 50.0,
        "expect_ack": True,
    })

    # 1秒后发 STOP
    time.sleep(1)
    print("  -- 发送 STOP --")
    cid = cmd_id()
    acks = send_and_recv(sock, addr, {
        "cmd_id": cid,
        "action": "STOP",
        "expect_ack": True,
    })

    ok = check_ack(acks, "received") and check_ack(acks, "completed")
    print(f"  结果: {'✅ 通过' if ok else '❌ 失败'} (STOP 收到 {len(acks)} 条 ACK)")
    return ok


def test_emergency_stop_with_ack(sock, addr):
    """测试 4: 发送 MOVE，1秒后发送 EMERGENCY_STOP"""
    print("\n[测试4] EMERGENCY_STOP 中断 SPIN (带 ACK)")

    print("  -- 发送 SPIN(90) --")
    send_and_recv(sock, addr, {
        "cmd_id": cmd_id(),
        "action": "SPIN",
        "target": 90.0,
        "expect_ack": True,
    })

    time.sleep(1)
    print("  -- 发送 EMERGENCY_STOP --")
    cid = cmd_id()
    acks = send_and_recv(sock, addr, {
        "cmd_id": cid,
        "action": "EMERGENCY_STOP",
        "expect_ack": True,
    })

    ok = check_ack(acks, "received") and check_ack(acks, "completed")
    print(f"  结果: {'✅ 通过' if ok else '❌ 失败'} (收到 {len(acks)} 条 ACK)")
    return ok


def test_unknown_action(sock, addr):
    """测试 5: 不支持的 action → 期望收到 failed ACK"""
    print("\n[测试5] 不支持的 action (带 ACK)")
    cid = cmd_id()
    acks = send_and_recv(sock, addr, {
        "cmd_id": cid,
        "action": "DANCE",
        "expect_ack": True,
    })

    ok = check_ack(acks, "failed", "error")
    print(f"  结果: {'✅ 通过' if ok else '❌ 失败'}")
    return ok


def test_move_no_ack(sock, addr):
    """测试 6: MOVE 不带 ACK → 期望无回复（原有行为兼容）"""
    print("\n[测试6] MOVE 不带 expect_ack (应无回复)")
    acks = send_and_recv(sock, addr, {
        "action": "MOVE",
        "target": 3.0,
    })

    ok = len(acks) == 0
    print(f"  结果: {'✅ 通过' if ok else '❌ 失败'} (收到 {len(acks)} 条回复)")
    return ok


def test_stop_clears_queue(sock, addr):
    """测试 7: 快速发 3 条 MOVE + 1 条 STOP → 期望后续命令不被执行"""
    print("\n[测试7] STOP 清空队列 (快速发 3 条 MOVE 后 STOP)")

    for i in range(3):
        send_and_recv(sock, addr, {
            "cmd_id": cmd_id(),
            "action": "MOVE",
            "target": 5.0,
            "expect_ack": True,
        })
        time.sleep(0.1)

    time.sleep(0.3)
    print("  -- 发送 STOP --")
    acks = send_and_recv(sock, addr, {
        "cmd_id": cmd_id(),
        "action": "STOP",
        "expect_ack": True,
    })

    # 再等几秒，如果队列清空了，不应该再有 completed 到来
    time.sleep(2)
    extra = []
    try:
        while True:
            resp, _ = sock.recvfrom(4096)
            decoded = resp.decode()
            print(f"  <<< (延迟) {decoded}")
            extra.append(json.loads(decoded))
    except socket.timeout:
        pass

    ok = check_ack(acks, "completed") and len(extra) == 0
    print(f"  结果: {'✅ 通过' if ok else '❌ 失败'} (STOP ACK: {len(acks)}, 延迟 ACK: {len(extra)})")
    return ok


# ─── 主程序 ──────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <D-BOT的IP地址>")
        print(f"示例: python3 {sys.argv[0]} 192.168.1.100")
        sys.exit(1)

    ip = sys.argv[1]
    addr = (ip, UDP_PORT)
    sock = make_sock()

    print(f"目标: {ip}:{UDP_PORT}")
    print("=" * 50)

    tests = [
        test_move_no_ack,
        test_move_with_ack,
        test_spin_with_ack,
        test_stop_with_ack,
        test_emergency_stop_with_ack,
        test_unknown_action,
        test_stop_clears_queue,
    ]

    results = []
    for t in tests:
        try:
            results.append((t.__doc__, t(sock, addr)))
        except Exception as e:
            results.append((t.__doc__, False))
            print(f"  ❌ 异常: {e}")
        time.sleep(1)

    sock.close()

    print("\n" + "=" * 50)
    print("汇总:")
    for desc, ok in results:
        print(f"  {'✅' if ok else '❌'} {desc}")

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n通过: {passed}/{total}")


if __name__ == "__main__":
    main()
