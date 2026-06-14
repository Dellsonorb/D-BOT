# -*- coding: utf-8 -*-
"""
D-BOT 可视化面板组件.

显示 D-BOT 机器人的实时状态，并提供手动控制按钮。
所有操作均通过 ThingManager.invoke() 走标准 Thing 机制。
"""

import asyncio
import json
import logging
from typing import Optional

from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

# D-BOT Thing 名称（与 dbot.py 中注册的一致）
_THING_NAME = "DBot"

# 状态刷新间隔（毫秒）
_REFRESH_INTERVAL_MS = 1000

# 结果显示区最大行数
_MAX_RESULT_LINES = 50


class _AsyncBridge(QObject):
    """在 Qt 信号中转接 asyncio 协程，确保线程安全。"""

    result_ready = pyqtSignal(str, str)  # (button_label, result_text)


def _make_status_row(labels_dict, key, label_text, grid, row, col):
    """在 grid 的 (row, col*2) 和 (row, col*2+1) 位置创建标签和值。"""
    lbl = QLabel(f"{label_text}:")
    lbl.setStyleSheet("font-weight: normal; color: #666; font-size: 11px;")
    val = QLabel("—")
    val.setWordWrap(True)
    val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    val.setStyleSheet("font-size: 11px;")
    grid.addWidget(lbl, row, col * 2)
    grid.addWidget(val, row, col * 2 + 1)
    labels_dict[key] = val


class DBotPanel(QWidget):
    """
    D-BOT 状态面板 — 嵌入主窗口的侧边栏组件。

    功能：
    - 实时显示 D-BOT 在线状态、IP、端口、忙碌状态、ACK 状态等
    - 提供手动控制按钮（前进/后退/左转/右转/停止/紧急停止/Ping）
    - 提供动作组合按钮（正方形/演示）
    - 每秒自动刷新状态
    - 所有按钮操作通过 ThingManager.invoke() 调用
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._bridge = _AsyncBridge()
        self._bridge.result_ready.connect(self._on_result_ready)
        self._init_ui()
        self._start_refresh_timer()
        logger.info("D-BOT 面板已初始化")

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self):
        """构建面板界面。"""
        self.setMinimumWidth(380)
        self.setMaximumWidth(460)
        self.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #d0d5dd;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
            QLabel {
                font-size: 11px;
            }
            QPushButton {
                font-size: 11px;
                min-height: 26px;
                border: 1px solid #d0d5dd;
                border-radius: 4px;
                padding: 2px 6px;
                background-color: #f7f8fa;
            }
            QPushButton:hover {
                background-color: #e8e9ec;
            }
            QPushButton:pressed {
                background-color: #d0d5dd;
            }
            QPushButton#pingBtn {
                background-color: #e6f4ea;
                border-color: #a8dab5;
            }
            QPushButton#pingBtn:hover {
                background-color: #d0e8d6;
            }
            QPushButton#stopBtn {
                background-color: #fde8e8;
                border-color: #f5a8a8;
            }
            QPushButton#stopBtn:hover {
                background-color: #f5d0d0;
            }
            QPushButton#estopBtn {
                background-color: #ff4444;
                border-color: #cc0000;
                color: white;
                font-weight: bold;
            }
            QPushButton#estopBtn:hover {
                background-color: #cc0000;
            }
            QPushButton#seqBtn {
                background-color: #e8f0fe;
                border-color: #a0c0f0;
            }
            QPushButton#seqBtn:hover {
                background-color: #d0e0f8;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QTextEdit {
                font-size: 11px;
                font-family: 'Courier New', monospace;
                background-color: #fafbfc;
                border: 1px solid #e5e6eb;
                border-radius: 4px;
            }
        """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(2)

        # 可滚动区域，防止面板内容溢出
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_layout.setSpacing(4)

        # ---- 顶部状态：两列紧凑网格 ----
        status_group = QGroupBox("状态")
        status_grid = QGridLayout(status_group)
        status_grid.setContentsMargins(8, 12, 8, 8)
        status_grid.setHorizontalSpacing(8)
        status_grid.setVerticalSpacing(2)

        self._status_labels = {}

        # 第 0 行：在线 / 忙碌
        _make_status_row(self._status_labels, "online", "在线", status_grid, 0, 0)
        _make_status_row(self._status_labels, "busy", "忙碌", status_grid, 0, 1)
        # 第 1 行：机器人状态 / 协议
        _make_status_row(self._status_labels, "robot_status", "状态", status_grid, 1, 0)
        _make_status_row(self._status_labels, "protocol", "协议", status_grid, 1, 1)
        # 第 2 行：IP / 端口
        _make_status_row(self._status_labels, "ip_address", "IP", status_grid, 2, 0)
        _make_status_row(self._status_labels, "port", "端口", status_grid, 2, 1)
        # 第 3 行：最近动作 / 最近结果（整行）
        _make_status_row(self._status_labels, "last_action", "最近动作", status_grid, 3, 0)
        _make_status_row(self._status_labels, "last_result", "最近结果", status_grid, 3, 1)
        # 第 4 行：最近错误（整行，红色高亮）
        _make_status_row(self._status_labels, "last_error", "最近错误", status_grid, 4, 0)
        # 占位
        status_grid.addWidget(QWidget(), 4, 1)

        scroll_layout.addWidget(status_group)

        # ---- ACK 状态：独立分组 ----
        ack_group = QGroupBox("ACK 回执")
        ack_grid = QGridLayout(ack_group)
        ack_grid.setContentsMargins(8, 12, 8, 8)
        ack_grid.setHorizontalSpacing(8)
        ack_grid.setVerticalSpacing(2)

        # 第 0 行：ACK 启用 / ACK 阶段
        _make_status_row(self._status_labels, "ack_enabled", "ACK 启用", ack_grid, 0, 0)
        _make_status_row(self._status_labels, "last_ack_stage", "ACK 阶段", ack_grid, 0, 1)
        # 第 1 行：命令 ID（整行）
        _make_status_row(self._status_labels, "last_command_id", "命令 ID", ack_grid, 1, 0)
        _make_status_row(self._status_labels, "last_ack_time", "ACK 时间", ack_grid, 1, 1)
        # 第 2 行：ACK 信息（整行）
        _make_status_row(self._status_labels, "last_ack_message", "ACK 信息", ack_grid, 2, 0)
        # 占位
        ack_grid.addWidget(QWidget(), 2, 1)

        scroll_layout.addWidget(ack_group)

        # ---- 手动控制按钮 ----
        control_group = QGroupBox("手动控制")
        control_grid = QGridLayout(control_group)
        control_grid.setContentsMargins(8, 12, 8, 8)
        control_grid.setSpacing(4)

        # 3 列网格布局
        btn_fwd = QPushButton("▲ 前进")
        btn_fwd.clicked.connect(lambda: self._invoke_method("GoForwardALittle", {}))
        btn_bwd = QPushButton("▼ 后退")
        btn_bwd.clicked.connect(lambda: self._invoke_method("GoBackwardALittle", {}))
        btn_left = QPushButton("◀ 左转")
        btn_left.clicked.connect(lambda: self._invoke_method("TurnLeftALittle", {}))
        btn_right = QPushButton("▶ 右转")
        btn_right.clicked.connect(lambda: self._invoke_method("TurnRightALittle", {}))
        btn_around = QPushButton("↻ 掉头")
        btn_around.clicked.connect(lambda: self._invoke_method("TurnAround", {}))
        btn_ping = QPushButton("🔍 Ping")
        btn_ping.setObjectName("pingBtn")
        btn_ping.clicked.connect(lambda: self._invoke_method("Ping", {}))

        control_grid.addWidget(btn_fwd,    0, 0)
        control_grid.addWidget(btn_bwd,    0, 1)
        control_grid.addWidget(btn_around, 0, 2)
        control_grid.addWidget(btn_left,   1, 0)
        control_grid.addWidget(btn_right,  1, 1)
        control_grid.addWidget(btn_ping,   1, 2)

        # 停止 / 急停
        btn_stop = QPushButton("■ 停止")
        btn_stop.setObjectName("stopBtn")
        btn_stop.clicked.connect(lambda: self._invoke_method("Stop", {}))
        btn_estop = QPushButton("⚠ 急停")
        btn_estop.setObjectName("estopBtn")
        btn_estop.clicked.connect(lambda: self._invoke_method("EmergencyStop", {}))

        control_grid.addWidget(btn_stop,  2, 0, 1, 2)  # 跨 2 列
        control_grid.addWidget(btn_estop, 2, 2)

        scroll_layout.addWidget(control_group)

        # ---- 动作组合 ----
        seq_group = QGroupBox("动作组合")
        seq_grid = QGridLayout(seq_group)
        seq_grid.setContentsMargins(8, 12, 8, 8)
        seq_grid.setSpacing(4)

        btn_square = QPushButton("⬜ 正方形")
        btn_square.setObjectName("seqBtn")
        btn_square.clicked.connect(lambda: self._invoke_method("SquarePatrol", {}))
        btn_demo = QPushButton("💃 演示")
        btn_demo.setObjectName("seqBtn")
        btn_demo.clicked.connect(lambda: self._invoke_method("DemoDance", {}))
        btn_fwd10 = QPushButton("→ 10cm")
        btn_fwd10.setObjectName("seqBtn")
        btn_fwd10.clicked.connect(lambda: self._invoke_method("MoveForward", {"distance_cm": 10.0}))
        btn_left90 = QPushButton("↰ 90°")
        btn_left90.setObjectName("seqBtn")
        btn_left90.clicked.connect(lambda: self._invoke_method("TurnLeft", {"angle_deg": 90.0}))

        seq_grid.addWidget(btn_square, 0, 0)
        seq_grid.addWidget(btn_demo,   0, 1)
        seq_grid.addWidget(btn_fwd10,  1, 0)
        seq_grid.addWidget(btn_left90, 1, 1)

        scroll_layout.addWidget(seq_group)

        # ---- 执行结果日志 ----
        log_group = QGroupBox("执行结果")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 12, 8, 8)

        self._result_log = QTextEdit()
        self._result_log.setReadOnly(True)
        self._result_log.setMinimumHeight(120)
        log_layout.addWidget(self._result_log)

        scroll_layout.addWidget(log_group, 1)  # stretch=1 让日志区占剩余空间

        scroll.setWidget(scroll_widget)
        root_layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # 状态刷新
    # ------------------------------------------------------------------

    def _start_refresh_timer(self):
        """启动定时刷新。"""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._schedule_refresh)
        self._refresh_timer.start(_REFRESH_INTERVAL_MS)

    def _schedule_refresh(self):
        """将异步状态刷新调度到事件循环。"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._do_refresh())
        except RuntimeError:
            pass  # 事件循环未就绪，跳过

    async def _do_refresh(self):
        """从 ThingManager 获取 D-BOT 状态并更新 UI。"""
        try:
            from src.iot.thing_manager import ThingManager

            manager = ThingManager.get_instance()
            if not manager or not manager.things:
                return

            _changed, states_json = await manager.get_states_json(delta=False)
            states = json.loads(states_json) if states_json else []

            dbot_state = None
            for item in states:
                if item.get("name") == _THING_NAME:
                    dbot_state = item.get("state", {})
                    break

            if dbot_state is None:
                return

            self._update_status_labels(dbot_state)
        except Exception as e:
            logger.debug(f"D-BOT 状态刷新失败: {e}")

    def _update_status_labels(self, state: dict):
        """用 state dict 更新所有状态标签。"""
        for key, label in self._status_labels.items():
            value = state.get(key, "—")
            # 格式化布尔值
            if isinstance(value, bool):
                text = "是" if value else "否"
            elif value is None:
                text = "—"
            elif isinstance(value, (dict, list)):
                text = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, float) and value > 0 and key == "last_ack_time":
                # 格式化时间戳
                from datetime import datetime
                text = datetime.fromtimestamp(value).strftime("%H:%M:%S")
            else:
                text = str(value)

            # 截断过长的 cmd_id
            if key == "last_command_id" and len(text) > 16:
                text = text[:16] + "…"

            # 着色逻辑
            if key == "online":
                if value is True:
                    label.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 11px;")
                elif value is False:
                    label.setStyleSheet("color: #dc2626; font-weight: bold; font-size: 11px;")
                else:
                    label.setStyleSheet("font-size: 11px;")
            elif key == "busy":
                if value is True:
                    label.setStyleSheet("color: #d97706; font-weight: bold; font-size: 11px;")
                else:
                    label.setStyleSheet("font-size: 11px;")
            elif key == "last_error":
                if value and value != "—":
                    label.setStyleSheet("color: #dc2626; font-size: 11px;")
                else:
                    label.setStyleSheet("font-size: 11px;")
            elif key == "last_ack_stage":
                # ACK 阶段着色
                if value == "received":
                    label.setStyleSheet("color: #2563eb; font-weight: bold; font-size: 11px;")
                elif value == "started":
                    label.setStyleSheet("color: #d97706; font-weight: bold; font-size: 11px;")
                elif value == "completed":
                    label.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 11px;")
                elif value == "failed":
                    label.setStyleSheet("color: #dc2626; font-weight: bold; font-size: 11px;")
                elif value == "timeout":
                    label.setStyleSheet("color: #6b7280; font-weight: bold; font-size: 11px;")
                else:
                    label.setStyleSheet("font-size: 11px;")
            elif key == "robot_status":
                # 机器人状态着色
                if value in ("idle",):
                    label.setStyleSheet("color: #16a34a; font-size: 11px;")
                elif value in ("waiting_ack", "command_received"):
                    label.setStyleSheet("color: #2563eb; font-size: 11px;")
                elif value in ("moving", "spinning"):
                    label.setStyleSheet("color: #d97706; font-weight: bold; font-size: 11px;")
                elif value in ("stopping",):
                    label.setStyleSheet("color: #d97706; font-size: 11px;")
                elif value in ("error",):
                    label.setStyleSheet("color: #dc2626; font-weight: bold; font-size: 11px;")
                elif value in ("offline",):
                    label.setStyleSheet("color: #6b7280; font-size: 11px;")
                else:
                    label.setStyleSheet("font-size: 11px;")

            label.setText(text)

    # ------------------------------------------------------------------
    # 按钮操作 — 全部走 ThingManager.invoke()
    # ------------------------------------------------------------------

    def _invoke_method(self, method_name: str, parameters: dict):
        """
        通过 ThingManager.invoke() 调用 D-BOT Thing 方法。
        在 Qt 线程中调度异步任务。
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._do_invoke(method_name, parameters))
            else:
                logger.warning("事件循环未运行，无法调用 D-BOT 方法")
        except RuntimeError as e:
            logger.error(f"调度 D-BOT 调用失败: {e}")

    async def _do_invoke(self, method_name: str, parameters: dict):
        """异步执行 Thing invoke 并回调显示结果。"""
        try:
            from src.iot.thing_manager import ThingManager

            manager = ThingManager.get_instance()
            command = {
                "name": _THING_NAME,
                "method": method_name,
                "parameters": parameters,
            }

            logger.info(f"D-BOT 调用: {method_name}({parameters})")
            result = await manager.invoke(command)

            result_text = json.dumps(result, ensure_ascii=False, indent=2) if result else "(无返回)"
            logger.info(f"D-BOT 结果: {result_text}")

            self._bridge.result_ready.emit(method_name, result_text)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.error(f"D-BOT 调用异常: {error_msg}")
            self._bridge.result_ready.emit(method_name, f"[错误] {error_msg}")

    def _on_result_ready(self, method_name: str, result_text: str):
        """在 Qt 主线程中更新结果日志。"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._result_log.append(f"[{timestamp}] {method_name}")
        self._result_log.append(result_text)
        self._result_log.append("")

        # 限制行数
        doc = self._result_log.document()
        if doc.blockCount() > _MAX_RESULT_LINES:
            cursor = self._result_log.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, doc.blockCount() - _MAX_RESULT_LINES)
            cursor.removeSelectedText()
