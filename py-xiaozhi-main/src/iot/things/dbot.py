import asyncio
import json
import time
from typing import Any, Dict, List

from src.iot.thing import Parameter, Thing, ValueType
from src.iot.things.dbot_client import DBotClient
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DBotThing(Thing):
    """将 D-BOT 注册为 py-xiaozhi 的标准 Thing。"""

    def __init__(self, config: Dict[str, Any] | None = None):
        cfg = config or {}
        name = cfg.get("NAME", "DBot")
        description = cfg.get(
            "DESCRIPTION",
            "D-BOT 智能移动机器人，可执行前进、后退、旋转和停止等动作",
        )
        super().__init__(name, description)

        self.logger = logger
        self._lock = asyncio.Lock()

        self.ip_address = cfg.get("IP_ADDRESS", "192.168.1.100")
        self.port = int(cfg.get("PORT", 6090))
        self.protocol = "udp"
        self.timeout_sec = float(cfg.get("TIMEOUT_SEC", 1.5))
        self.enable_ping_check = bool(cfg.get("ENABLE_PING_CHECK", True))
        self.forward_move_positive = bool(cfg.get("FORWARD_MOVE_POSITIVE", True))
        self.left_spin_positive = bool(cfg.get("LEFT_SPIN_POSITIVE", True))
        self.enable_stop_fallback = bool(cfg.get("ENABLE_STOP_FALLBACK", True))
        self.max_distance_cm = float(cfg.get("MAX_DISTANCE_CM", 300.0))
        self.max_angle_deg = float(cfg.get("MAX_ANGLE_DEG", 360.0))
        self.status_stale_sec = float(cfg.get("STATUS_STALE_SEC", 30.0))

        # ACK 配置
        self.expect_ack = bool(cfg.get("EXPECT_ACK", True))
        self.ack_timeout_sec = float(cfg.get("ACK_TIMEOUT_SEC", 10.0))
        self.ack_listen_port = int(cfg.get("ACK_LISTEN_PORT", 16090))
        self.default_action_delay_sec = float(cfg.get("DEFAULT_ACTION_DELAY_SEC", 1.5))
        self.sequence_step_delay_sec = float(cfg.get("SEQUENCE_STEP_DELAY_SEC", 0.2))

        self.client = DBotClient(
            host=self.ip_address,
            port=self.port,
            timeout_sec=self.timeout_sec,
            enable_ping_check=self.enable_ping_check,
            expect_ack=self.expect_ack,
            ack_timeout_sec=self.ack_timeout_sec,
            ack_listen_port=self.ack_listen_port,
        )

        self.online = False
        self.busy = False
        self.robot_status = "idle"
        self.last_action = ""
        self.last_parameters: Dict[str, Any] = {}
        self.last_result = ""
        self.last_error = ""
        self.pending_command_count = 0
        self.last_seen = 0.0
        self.last_command_payload: Dict[str, Any] = {}

        # ACK 状态字段
        self.last_command_id: str = ""
        self.last_ack_stage: str = ""
        self.last_ack_message: str = ""
        self.last_ack_raw: str = ""
        self.last_ack_time: float = 0.0

        # ---- 属性注册 ----
        self.add_property("online", "D-BOT 当前是否在线", self.get_online)
        self.add_property("busy", "D-BOT 当前是否正在执行动作", self.get_busy)
        self.add_property("robot_status", "D-BOT 当前状态", self.get_robot_status)
        self.add_property("ip_address", "D-BOT 当前目标 IP 地址", self.get_ip_address)
        self.add_property("port", "D-BOT 当前目标 UDP 端口", self.get_port)
        self.add_property("protocol", "D-BOT 当前通信协议", self.get_protocol)
        self.add_property("last_action", "D-BOT 最后一次执行的方法名", self.get_last_action)
        self.add_property("last_parameters", "D-BOT 最后一次执行参数", self.get_last_parameters)
        self.add_property("last_result", "D-BOT 最近一次执行结果", self.get_last_result)
        self.add_property("last_error", "D-BOT 最近一次错误信息", self.get_last_error)
        self.add_property(
            "pending_command_count",
            "D-BOT 当前待处理命令数（本地估计值）",
            self.get_pending_command_count,
        )
        self.add_property("last_seen", "最近一次在线探测成功时间戳", self.get_last_seen)
        self.add_property(
            "last_command_payload",
            "最近一次发给 D-BOT 的底层 UDP JSON 载荷",
            self.get_last_command_payload,
        )
        # ACK 属性
        self.add_property("ack_enabled", "ACK 回执是否启用", self.get_ack_enabled)
        self.add_property("last_command_id", "最近一次命令 ID", self.get_last_command_id)
        self.add_property("last_ack_stage", "最近一次 ACK 阶段", self.get_last_ack_stage)
        self.add_property("last_ack_message", "最近一次 ACK 信息", self.get_last_ack_message)
        self.add_property("last_ack_raw", "最近一次 ACK 原始 JSON", self.get_last_ack_raw)
        self.add_property("last_ack_time", "最近一次 ACK 接收时间戳", self.get_last_ack_time)

        # ---- 方法注册 ----
        self.add_method("Ping", "检查 D-BOT 是否在线", [], self._ping)
        self.add_method(
            "Move",
            "按距离移动，正负方向由 D-BOT 安装和配置决定",
            [Parameter("distance_cm", "移动距离（厘米）", ValueType.FLOAT, True)],
            self._move,
        )
        self.add_method(
            "Spin",
            "按角度旋转，正负方向由 D-BOT 安装和配置决定",
            [Parameter("angle_deg", "旋转角度（度）", ValueType.FLOAT, True)],
            self._spin,
        )
        self.add_method(
            "MoveForward",
            "向前移动指定距离（厘米）",
            [Parameter("distance_cm", "向前移动距离（厘米）", ValueType.FLOAT, True)],
            self._move_forward,
        )
        self.add_method(
            "MoveBackward",
            "向后移动指定距离（厘米）",
            [Parameter("distance_cm", "向后移动距离（厘米）", ValueType.FLOAT, True)],
            self._move_backward,
        )
        self.add_method(
            "TurnLeft",
            "向左旋转指定角度（度）",
            [Parameter("angle_deg", "向左旋转角度（度）", ValueType.FLOAT, True)],
            self._turn_left,
        )
        self.add_method(
            "TurnRight",
            "向右旋转指定角度（度）",
            [Parameter("angle_deg", "向右旋转角度（度）", ValueType.FLOAT, True)],
            self._turn_right,
        )
        self.add_method("Stop", "停止当前动作", [], self._stop)
        self.add_method("EmergencyStop", "紧急停止", [], self._emergency_stop)
        self.add_method(
            "SetTargetIp",
            "动态修改 D-BOT 的目标 IP 地址，便于重新配网后切换",
            [Parameter("ip_address", "新的目标 IP 地址", ValueType.STRING, True)],
            self._set_target_ip,
        )

        # 动作组合方法
        self.add_method(
            "RunSequence",
            "执行动作序列（JSON 数组或字符串）",
            [Parameter("sequence", "动作序列 JSON", ValueType.STRING, True)],
            self._run_sequence,
        )
        self.add_method(
            "SquarePatrol",
            "走正方形路径",
            [
                Parameter("side_cm", "边长（厘米）", ValueType.FLOAT, False),
                Parameter("turn_deg", "转弯角度（度）", ValueType.FLOAT, False),
            ],
            self._square_patrol,
        )
        self.add_method("DemoDance", "执行演示动作", [], self._demo_dance)

        # 高层语义方法
        self.add_method("GoForwardALittle", "向前走一点", [], self._go_forward_a_little)
        self.add_method("GoBackwardALittle", "向后退一点", [], self._go_backward_a_little)
        self.add_method("TurnLeftALittle", "左转一下", [], self._turn_left_a_little)
        self.add_method("TurnRightALittle", "右转一下", [], self._turn_right_a_little)
        self.add_method("TurnAround", "掉头（旋转 180°）", [], self._turn_around)
        self.add_method("PerformDemo", "做一个演示动作", [], self._perform_demo)

    # ------------------------------------------------------------------
    # 属性 Getter
    # ------------------------------------------------------------------

    async def get_online(self):
        self.online = await self.client.ping(force=False)
        if self.online:
            self.last_seen = time.time()
        else:
            if self.busy:
                self.robot_status = "error"
        return self.online

    async def get_busy(self):
        return self.busy

    async def get_robot_status(self):
        if self.robot_status != "error" and not await self.client.ping(force=False):
            if time.time() - self.last_seen > self.status_stale_sec:
                return "offline"
        return self.robot_status

    async def get_ip_address(self):
        return self.ip_address

    async def get_port(self):
        return self.port

    async def get_protocol(self):
        return self.protocol

    async def get_last_action(self):
        return self.last_action

    async def get_last_parameters(self):
        return self.last_parameters

    async def get_last_result(self):
        return self.last_result

    async def get_last_error(self):
        return self.last_error

    async def get_pending_command_count(self):
        return self.pending_command_count

    async def get_last_seen(self):
        return self.last_seen

    async def get_last_command_payload(self):
        return self.last_command_payload

    async def get_ack_enabled(self):
        return self.expect_ack

    async def get_last_command_id(self):
        return self.last_command_id

    async def get_last_ack_stage(self):
        return self.last_ack_stage

    async def get_last_ack_message(self):
        return self.last_ack_message

    async def get_last_ack_raw(self):
        return self.last_ack_raw

    async def get_last_ack_time(self):
        return self.last_ack_time

    # ------------------------------------------------------------------
    # 基础方法
    # ------------------------------------------------------------------

    async def _ping(self, params):
        online = await self.client.ping(force=True)
        self.online = online
        if online:
            self.last_seen = time.time()
            self.robot_status = "idle" if not self.busy else self.robot_status
            self.last_error = ""
            message = f"D-BOT 在线：{self.ip_address}:{self.port}"
            return {"status": "success", "message": message, "online": True}

        self.robot_status = "offline"
        self.last_error = f"D-BOT 不在线：{self.ip_address}:{self.port}"
        return {"status": "error", "message": self.last_error, "online": False}

    async def _move(self, params):
        distance_cm = float(params["distance_cm"].get_value())
        self._validate_distance(distance_cm)
        return await self._execute_motion(
            method_name="Move",
            action="MOVE",
            target=distance_cm,
            public_message=f"移动 {distance_cm} cm",
        )

    async def _spin(self, params):
        angle_deg = float(params["angle_deg"].get_value())
        self._validate_angle(angle_deg)
        return await self._execute_motion(
            method_name="Spin",
            action="SPIN",
            target=angle_deg,
            public_message=f"旋转 {angle_deg}°",
        )

    async def _move_forward(self, params):
        distance_cm = abs(float(params["distance_cm"].get_value()))
        self._validate_distance(distance_cm)
        signed_distance = distance_cm if self.forward_move_positive else -distance_cm
        return await self._execute_motion(
            method_name="MoveForward",
            action="MOVE",
            target=signed_distance,
            public_message=f"向前移动 {distance_cm} cm",
        )

    async def _move_backward(self, params):
        distance_cm = abs(float(params["distance_cm"].get_value()))
        self._validate_distance(distance_cm)
        signed_distance = -distance_cm if self.forward_move_positive else distance_cm
        return await self._execute_motion(
            method_name="MoveBackward",
            action="MOVE",
            target=signed_distance,
            public_message=f"向后移动 {distance_cm} cm",
        )

    async def _turn_left(self, params):
        angle_deg = abs(float(params["angle_deg"].get_value()))
        self._validate_angle(angle_deg)
        signed_angle = angle_deg if self.left_spin_positive else -angle_deg
        return await self._execute_motion(
            method_name="TurnLeft",
            action="SPIN",
            target=signed_angle,
            public_message=f"向左旋转 {angle_deg}°",
        )

    async def _turn_right(self, params):
        angle_deg = abs(float(params["angle_deg"].get_value()))
        self._validate_angle(angle_deg)
        signed_angle = -angle_deg if self.left_spin_positive else angle_deg
        return await self._execute_motion(
            method_name="TurnRight",
            action="SPIN",
            target=signed_angle,
            public_message=f"向右旋转 {angle_deg}°",
        )

    async def _stop(self, params):
        result = await self._execute_motion(
            method_name="Stop",
            action="STOP",
            target=0.0,
            public_message="停止动作",
        )
        return result

    async def _emergency_stop(self, params):
        result = await self._execute_motion(
            method_name="EmergencyStop",
            action="EMERGENCY_STOP",
            target=0.0,
            public_message="紧急停止",
        )
        return result

    async def _set_target_ip(self, params):
        ip_address = str(params["ip_address"].get_value()).strip()
        if not ip_address:
            return {"status": "error", "message": "ip_address 不能为空"}
        self.ip_address = ip_address
        self.client.set_target(ip_address, self.port)
        self.last_result = f"目标 IP 已更新为 {ip_address}:{self.port}"
        self.last_error = ""
        return {"status": "success", "message": self.last_result, "ip_address": ip_address}

    # ------------------------------------------------------------------
    # 核心动作执行（支持 ACK）
    # ------------------------------------------------------------------

    async def _execute_motion(
        self,
        method_name: str,
        action: str,
        target: float,
        public_message: str,
    ):
        async with self._lock:
            self.pending_command_count += 1
            self.last_action = method_name
            self.last_parameters = {"action": action, "target": target}
            self.last_command_payload = {"action": action, "target": target}
            self.last_error = ""

            # ACK 模式下的状态映射
            ack_status_map = {
                "MOVE": "moving",
                "SPIN": "spinning",
                "STOP": "stopping",
                "EMERGENCY_STOP": "stopping",
            }

            try:
                online = await self.client.ping(force=False)
                self.online = online
                if online:
                    self.last_seen = time.time()

                if self.expect_ack:
                    # ACK 模式：等待回执
                    self.busy = True
                    self.robot_status = "waiting_ack"

                    send_result = await self.client.send_action(action=action, target=target)

                    # 更新 cmd_id
                    self.last_command_id = send_result.get("cmd_id", "")

                    # 检查是否回退到 fire-and-forget（ACK 监听器不可用）
                    if send_result.get("ack_fallback"):
                        self.robot_status = ack_status_map.get(action, "moving")
                        self.last_result = f"{public_message}：指令已发送（ACK 监听器不可用，未等待回执）"
                        return {
                            "status": "success",
                            "message": self.last_result,
                            "ack_fallback": True,
                            "transport_result": send_result,
                        }

                    if not send_result.get("success"):
                        stage = send_result.get("stage", "")
                        if stage == "timeout":
                            self.robot_status = "error"
                            self.last_error = send_result.get("message", "ACK 超时")
                            self.last_result = ""
                            return {
                                "status": "timeout",
                                "message": self.last_error,
                                "cmd_id": self.last_command_id,
                            }
                        else:
                            self.robot_status = "error"
                            self.last_error = send_result.get("message", "未知错误")
                            self.last_result = ""
                            return {
                                "status": "error",
                                "message": self.last_error,
                                "cmd_id": self.last_command_id,
                            }

                    # 成功：更新状态
                    self.robot_status = "idle"
                    self.last_result = f"{public_message}：已完成"
                    return {
                        "status": "success",
                        "message": self.last_result,
                        "cmd_id": self.last_command_id,
                        "stage": send_result.get("stage", ""),
                    }
                else:
                    # Fire-and-forget 模式
                    self.busy = True
                    self.robot_status = ack_status_map.get(action, "moving")

                    send_result = await self.client.send_action(action=action, target=target)
                    if not send_result.get("success"):
                        self.robot_status = "error"
                        self.last_error = send_result.get("message", "未知错误")
                        self.last_result = ""
                        return {
                            "status": "error",
                            "message": self.last_error,
                            "transport_result": send_result,
                        }

                    self.robot_status = "idle"
                    self.last_result = f"{public_message}：指令已发送到 {self.ip_address}:{self.port}"
                    return {
                        "status": "success",
                        "message": self.last_result,
                        "transport_result": send_result,
                    }

            except Exception as exc:
                self.robot_status = "error"
                self.last_error = str(exc)
                self.last_result = ""
                self.logger.error("D-BOT 方法 %s 执行失败: %s", method_name, exc, exc_info=True)
                return {"status": "error", "message": f"{method_name} 执行失败: {exc}"}
            finally:
                self.busy = False
                self.pending_command_count = max(0, self.pending_command_count - 1)

    # ------------------------------------------------------------------
    # 动作组合方法
    # ------------------------------------------------------------------

    async def _run_sequence_impl(self, sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """内部方法：执行动作序列。"""
        results = []
        for i, step in enumerate(sequence):
            method_name = step.get("method", "")
            parameters = step.get("parameters", {})

            if not method_name:
                results.append({"step": i, "status": "error", "message": "缺少 method 字段"})
                break

            # 检查是否需要中止（Stop/EmergencyStop）
            if method_name in ("Stop", "EmergencyStop"):
                try:
                    command = {"name": self.name, "method": method_name, "parameters": {}}
                    result = await self.invoke(command)
                    results.append({"step": i, "method": method_name, "result": result})
                except Exception as e:
                    results.append({"step": i, "method": method_name, "error": str(e)})
                break

            try:
                command = {"name": self.name, "method": method_name, "parameters": parameters}
                result = await self.invoke(command)
                results.append({"step": i, "method": method_name, "result": result})

                # 如果某步失败，停止后续
                if isinstance(result, dict) and result.get("status") == "error":
                    self.logger.warning("D-BOT 序列第 %d 步失败，中止后续: %s", i, result.get("message"))
                    break
            except Exception as e:
                results.append({"step": i, "method": method_name, "error": str(e)})
                break

            # 步间延迟
            if not self.expect_ack:
                await asyncio.sleep(self.default_action_delay_sec)
            else:
                # ACK 模式下已完成等待，只需短暂停顿
                await asyncio.sleep(self.sequence_step_delay_sec)

        return {"status": "success", "message": f"序列执行完成，共 {len(results)} 步", "steps": results}

    async def _run_sequence(self, params):
        """执行动作序列（JSON 数组或字符串）。"""
        sequence_raw = params["sequence"].get_value()

        if isinstance(sequence_raw, str):
            try:
                sequence = json.loads(sequence_raw)
            except json.JSONDecodeError as e:
                return {"status": "error", "message": f"序列 JSON 解析失败: {e}"}
        elif isinstance(sequence_raw, list):
            sequence = sequence_raw
        else:
            return {"status": "error", "message": "sequence 参数必须是 JSON 数组或字符串"}

        if not sequence:
            return {"status": "error", "message": "序列为空"}

        return await self._run_sequence_impl(sequence)

    async def _square_patrol(self, params):
        """走正方形路径。"""
        side_cm = 20.0
        turn_deg = 90.0

        if "side_cm" in params:
            p = params["side_cm"]
            if p.get_value() is not None:
                side_cm = abs(float(p.get_value()))
        if "turn_deg" in params:
            p = params["turn_deg"]
            if p.get_value() is not None:
                turn_deg = abs(float(p.get_value()))

        self._validate_distance(side_cm)
        self._validate_angle(turn_deg)

        sequence = []
        for _ in range(4):
            sequence.append({"method": "MoveForward", "parameters": {"distance_cm": side_cm}})
            sequence.append({"method": "TurnLeft", "parameters": {"angle_deg": turn_deg}})

        return await self._run_sequence_impl(sequence)

    async def _demo_dance(self, params):
        """执行演示动作。"""
        sequence = [
            {"method": "MoveForward", "parameters": {"distance_cm": 10}},
            {"method": "MoveBackward", "parameters": {"distance_cm": 10}},
            {"method": "TurnLeft", "parameters": {"angle_deg": 45}},
            {"method": "TurnRight", "parameters": {"angle_deg": 45}},
            {"method": "TurnLeft", "parameters": {"angle_deg": 90}},
            {"method": "TurnRight", "parameters": {"angle_deg": 90}},
        ]
        return await self._run_sequence_impl(sequence)

    # ------------------------------------------------------------------
    # 高层语义方法
    # ------------------------------------------------------------------

    async def _go_forward_a_little(self, params):
        """向前走一点（默认 10 cm）。"""
        return await self._execute_motion(
            method_name="GoForwardALittle",
            action="MOVE",
            target=10.0 if self.forward_move_positive else -10.0,
            public_message="向前走一点（10 cm）",
        )

    async def _go_backward_a_little(self, params):
        """向后退一点（默认 10 cm）。"""
        return await self._execute_motion(
            method_name="GoBackwardALittle",
            action="MOVE",
            target=-10.0 if self.forward_move_positive else 10.0,
            public_message="向后退一点（10 cm）",
        )

    async def _turn_left_a_little(self, params):
        """左转一下（默认 30°）。"""
        return await self._execute_motion(
            method_name="TurnLeftALittle",
            action="SPIN",
            target=30.0 if self.left_spin_positive else -30.0,
            public_message="左转一下（30°）",
        )

    async def _turn_right_a_little(self, params):
        """右转一下（默认 30°）。"""
        return await self._execute_motion(
            method_name="TurnRightALittle",
            action="SPIN",
            target=-30.0 if self.left_spin_positive else 30.0,
            public_message="右转一下（30°）",
        )

    async def _turn_around(self, params):
        """掉头（旋转 180°）。"""
        return await self._execute_motion(
            method_name="TurnAround",
            action="SPIN",
            target=180.0 if self.left_spin_positive else -180.0,
            public_message="掉头（180°）",
        )

    async def _perform_demo(self, params):
        """做一个演示动作（调用 DemoDance）。"""
        return await self._demo_dance(params)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    async def close(self):
        """关闭 D-BOT Thing（清理 ACK 监听器等资源）。"""
        await self.client.close()

    def _validate_distance(self, distance_cm: float) -> None:
        if abs(distance_cm) > self.max_distance_cm:
            raise ValueError(
                f"distance_cm 超出安全范围：{distance_cm}，当前限制为 ±{self.max_distance_cm} cm"
            )

    def _validate_angle(self, angle_deg: float) -> None:
        if abs(angle_deg) > self.max_angle_deg:
            raise ValueError(
                f"angle_deg 超出安全范围：{angle_deg}，当前限制为 ±{self.max_angle_deg}°"
            )
