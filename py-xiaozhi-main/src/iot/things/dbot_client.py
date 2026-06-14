import asyncio
import json
import platform
import socket
import time
import uuid
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class _AckProtocol(asyncio.DatagramProtocol):
    """UDP 协议，用于接收 D-BOT 的 ACK 回执。"""

    def __init__(self, pending_cmds: Dict[str, asyncio.Future], client: "DBotClient"):
        self.pending_cmds = pending_cmds
        self.client = client
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        logger.info("D-BOT ACK 监听器已启动")

    def connection_lost(self, exc):
        logger.info("D-BOT ACK 监听器已停止")

    def datagram_received(self, data: bytes, addr):
        try:
            ack = json.loads(data.decode("utf-8"))
        except Exception as exc:
            logger.warning("D-BOT ACK 解析失败: %s, data=%r", exc, data)
            return

        cmd_id = ack.get("cmd_id", "")
        stage = ack.get("stage", "unknown")
        status = ack.get("status", "")
        message = ack.get("message", "")

        # 更新 client 的 ACK 状态字段（所有阶段都更新）
        self.client.last_ack = ack
        self.client.last_ack_stage = stage
        self.client.last_ack_message = message
        self.client.last_ack_raw = data.decode("utf-8", errors="replace")
        self.client.last_ack_time = time.time()
        self.client.last_command_id = cmd_id

        logger.info(
            "D-BOT ACK 收到: cmd_id=%s stage=%s status=%s message=%s",
            cmd_id, stage, status, message,
        )

        # 仅终态（completed/failed）才 resolve Future，中间阶段只记录
        if stage in ("completed", "failed"):
            if cmd_id in self.pending_cmds:
                future = self.pending_cmds[cmd_id]
                if not future.done():
                    future.set_result(ack)
            else:
                logger.debug("D-BOT ACK cmd_id=%s 无匹配的等待命令", cmd_id)
        else:
            logger.debug("D-BOT ACK 中间阶段: cmd_id=%s stage=%s，继续等待终态", cmd_id, stage)


class DBotClient:
    """D-BOT 的底层通信客户端。

    支持两种模式：
    1. fire-and-forget（EXPECT_ACK=false）：发送 UDP 后立即返回
    2. ACK 模式（EXPECT_ACK=true）：通过同一个 socket 发送命令并接收 ACK
    """

    def __init__(
        self,
        host: str,
        port: int = 6090,
        timeout_sec: float = 1.5,
        enable_ping_check: bool = True,
        ping_cache_ttl_sec: float = 3.0,
        expect_ack: bool = True,
        ack_timeout_sec: float = 10.0,
        ack_listen_port: int = 16090,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout_sec = timeout_sec
        self.enable_ping_check = enable_ping_check
        self.ping_cache_ttl_sec = ping_cache_ttl_sec
        self.expect_ack = expect_ack
        self.ack_timeout_sec = ack_timeout_sec
        self.ack_listen_port = ack_listen_port

        self._last_ping_ts: float = 0.0
        self._last_ping_result: Optional[bool] = None

        # ACK 相关状态
        self.last_command_id: str = ""
        self.last_ack: Optional[Dict[str, Any]] = None
        self.last_ack_stage: str = ""
        self.last_ack_message: str = ""
        self.last_ack_raw: str = ""
        self.last_ack_time: float = 0.0

        # ACK 监听器（同时用于发送）
        self._pending_cmds: Dict[str, asyncio.Future] = {}
        self._ack_transport: Optional[asyncio.DatagramTransport] = None
        self._ack_protocol: Optional[_AckProtocol] = None
        self._listener_started = False

    def set_target(self, host: str, port: Optional[int] = None) -> None:
        self.host = host
        if port is not None:
            self.port = port
        self._last_ping_ts = 0.0
        self._last_ping_result = None

    async def _ensure_ack_listener(self) -> bool:
        """懒启动 ACK UDP 监听器。返回是否可用。"""
        if self._listener_started and self._ack_transport is not None:
            return True
        try:
            loop = asyncio.get_running_loop()
            # 使用 SO_REUSEADDR 允许快速重绑定（避免上次残留 TIME_WAIT）
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", self.ack_listen_port))
            sock.setblocking(False)

            self._ack_transport, self._ack_protocol = await loop.create_datagram_endpoint(
                lambda: _AckProtocol(self._pending_cmds, self),
                sock=sock,
            )
            self._listener_started = True
            logger.info("D-BOT ACK 监听端口: %d", self.ack_listen_port)
            return True
        except OSError as exc:
            logger.warning(
                "D-BOT ACK 监听器启动失败（端口 %d）: %s，回退 fire-and-forget",
                self.ack_listen_port, exc,
            )
            self._listener_started = False
            return False

    async def send_action(self, action: str, target: float) -> Dict[str, Any]:
        """发送动作指令。根据 expect_ack 决定是否等待 ACK。"""
        if self.expect_ack:
            return await self.send_action_with_ack(action, target)
        else:
            return await self._send_fire_and_forget(action, target)

    async def send_action_with_ack(self, action: str, target: float) -> Dict[str, Any]:
        """发送动作指令并等待 ACK 回执。

        使用监听器的同一个 socket 发送，确保 D-BOT 的 ACK 回到本端口。
        """
        listener_ok = await self._ensure_ack_listener()
        if not listener_ok:
            # ACK 监听器不可用，回退 fire-and-forget
            logger.warning("D-BOT ACK 监听器不可用，回退 fire-and-forget 模式")
            result = await self._send_fire_and_forget(action, target)
            result["ack_fallback"] = True
            result["message"] += "（ACK 监听器不可用，已回退 fire-and-forget）"
            return result

        cmd_id = str(uuid.uuid4())
        self.last_command_id = cmd_id

        payload = {
            "cmd_id": cmd_id,
            "action": action,
            "target": target,
            "expect_ack": True,
        }

        # 注册 Future
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending_cmds[cmd_id] = future

        try:
            # 通过监听器的 transport 发送（D-BOT 会把 ACK 发回这个端口）
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._ack_transport.sendto(data, (self.host, self.port))
            logger.info(
                "D-BOT UDP 指令已发送: host=%s port=%s bytes=%d payload=%s",
                self.host, self.port, len(data), payload,
            )

            # 等待 ACK
            logger.info("D-BOT 等待 ACK: cmd_id=%s action=%s target=%s", cmd_id, action, target)
            ack = await asyncio.wait_for(future, timeout=self.ack_timeout_sec)

            stage = ack.get("stage", "")
            status = ack.get("status", "")
            message = ack.get("message", "")

            if stage == "completed" and status == "success":
                return {
                    "success": True,
                    "cmd_id": cmd_id,
                    "stage": stage,
                    "status": status,
                    "message": message or "动作已完成",
                    "ack": ack,
                }
            elif stage == "failed" or status == "error":
                return {
                    "success": False,
                    "cmd_id": cmd_id,
                    "stage": stage,
                    "status": status,
                    "message": message or "动作执行失败",
                    "ack": ack,
                }
            else:
                return {
                    "success": True,
                    "cmd_id": cmd_id,
                    "stage": stage,
                    "status": status,
                    "message": message or f"收到 ACK: {stage}",
                    "ack": ack,
                }

        except asyncio.TimeoutError:
            logger.warning("D-BOT ACK 超时: cmd_id=%s timeout=%.1fs", cmd_id, self.ack_timeout_sec)
            return {
                "success": False,
                "cmd_id": cmd_id,
                "stage": "timeout",
                "status": "timeout",
                "message": f"等待 ACK 超时（{self.ack_timeout_sec}s）",
                "ack": None,
            }
        except Exception as exc:
            logger.error("D-BOT ACK 等待异常: cmd_id=%s error=%s", cmd_id, exc, exc_info=True)
            return {
                "success": False,
                "cmd_id": cmd_id,
                "stage": "error",
                "status": "error",
                "message": f"ACK 等待异常: {exc}",
                "ack": None,
            }
        finally:
            self._pending_cmds.pop(cmd_id, None)

    async def _send_fire_and_forget(self, action: str, target: float) -> Dict[str, Any]:
        """Fire-and-forget 模式：发送后立即返回。"""
        payload = {"action": action, "target": target}
        result = await asyncio.to_thread(self._send_udp_packet_sync, payload)
        return result

    def _send_udp_packet_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """同步发送 UDP 数据包（在线程中运行）。仅用于 fire-and-forget 模式。"""
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout_sec)
        try:
            sent = sock.sendto(data, (self.host, self.port))
            logger.info(
                "D-BOT UDP 指令已发送: host=%s port=%s bytes=%s payload=%s",
                self.host,
                self.port,
                sent,
                payload,
            )
            return {
                "success": True,
                "transport": "udp",
                "host": self.host,
                "port": self.port,
                "bytes": sent,
                "payload": payload,
                "message": "UDP 指令已发送。注意：UDP 发送成功不等于 D-BOT 已完成动作。",
            }
        except Exception as exc:
            logger.error("D-BOT UDP 发送失败: %s", exc, exc_info=True)
            return {
                "success": False,
                "transport": "udp",
                "host": self.host,
                "port": self.port,
                "payload": payload,
                "message": f"UDP 指令发送失败: {exc}",
            }
        finally:
            sock.close()

    async def ping(self, force: bool = False) -> bool:
        if not self.enable_ping_check:
            return True

        now = time.monotonic()
        if (
            not force
            and self._last_ping_result is not None
            and now - self._last_ping_ts < self.ping_cache_ttl_sec
        ):
            return self._last_ping_result

        system_name = platform.system().lower()
        if system_name == "windows":
            cmd = ["ping", "-n", "1", "-w", str(int(self.timeout_sec * 1000)), self.host]
        else:
            wait_sec = str(max(1, int(round(self.timeout_sec))))
            cmd = ["ping", "-c", "1", "-W", wait_sec, self.host]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return_code = await proc.wait()
            online = return_code == 0
        except FileNotFoundError:
            logger.warning("系统未找到 ping 命令，在线检测退化为 True")
            online = True
        except Exception as exc:
            logger.warning("D-BOT ping 检测失败: %s", exc)
            online = False

        self._last_ping_ts = now
        self._last_ping_result = online
        return online

    async def close(self):
        """关闭 ACK 监听器。"""
        if self._ack_transport is not None:
            self._ack_transport.close()
            self._ack_transport = None
            self._ack_protocol = None
            self._listener_started = False
