# D-BOT PC 语音控制客户端 — 课程实践项目报告

## 一、项目背景

D-BOT 是一个基于 ESP32-S3 的开源桌面平衡机器人，原生支持通过"小智 AI"硬件设备进行语音控制。然而，小智 AI 硬件为专用设备，不易获取且成本较高。

本项目复现并扩展了 D-BOT 开源项目，基于 **py-xiaozhi**（小智 AI 的 Python PC 客户端复现版本），在 Linux PC 上实现了"小智硬件终端的软件替代"。在保留小智 IoT/Thing 机制的基础上，实现了 PC 端语音交互、GUI 显示、D-BOT Thing 注册、语音控制、手动控制、ACK 闭环、STOP/急停、动作组合和高层语义控制。

## 二、原始项目介绍

### 2.1 D-BOT

- **仓库地址**：https://github.com/dingmos/D-BOT
- **硬件平台**：ESP32-S3 + SimpleFOC 无刷电机驱动 + GC9A01 圆形 LCD
- **核心功能**：两轮自平衡、PID 运动控制、WiFi UDP 通信、BLE 手柄遥控
- **通信协议**：监听 UDP 6090 端口，接收 JSON 格式的动作指令（MOVE / SPIN / STOP / EMERGENCY_STOP）

### 2.2 py-xiaozhi

- **仓库地址**：https://github.com/Huang-junsen/py-xiaozhi
- **定位**：小智 AI 硬件的 Python PC 端复现
- **核心功能**：语音唤醒、语音识别、AI 对话、IoT 设备管理、PyQt5 GUI
- **IoT 机制**：通过 Thing 抽象层注册和管理外部设备，支持属性查询和方法调用

## 三、项目目标

1. 在 PC 上复现小智 AI 硬件的语音交互能力
2. 将 D-BOT 注册为 py-xiaozhi 的 IoT Thing，实现语音控制机器人
3. 增强 D-BOT 固件，支持 ACK 回执机制、STOP / EMERGENCY_STOP 指令
4. 实现动作组合（走正方形、演示动作）和高层语义控制（"向前走一点"、"掉头"等）
5. 在 GUI 中实时显示 ACK 状态和机器人控制面板

## 四、系统总体架构

```
┌─────────────────────────────────────────────────────┐
│                   Linux PC 端                         │
│                                                       │
│  ┌──────────┐    ┌───────────┐    ┌──────────────┐   │
│  │ 麦克风    │───▶│ py-xiaozhi │───▶│ ThingManager │   │
│  │ (音频输入) │    │           │    │              │   │
│  └──────────┘    │ - 语音识别 │    │  ┌─────────┐ │   │
│                  │ - AI 对话  │    │  │DBotThing│ │   │
│  ┌──────────┐    │ - GUI 界面 │    │  └────┬────┘ │   │
│  │ 扬声器    │◀──│           │    └───────┼──────┘   │
│  │ (音频输出) │    └───────────┘            │          │
│  └──────────┘                        ┌────▼─────┐    │
│                                      │DBotClient│    │
│  ┌──────────────────────┐            │ (UDP)    │    │
│  │ GUI (PyQt5 + QML)    │            └────┬─────┘    │
│  │ - 语音状态显示        │                 │          │
│  │ - D-BOT 控制面板      │                 │          │
│  │ - ACK 状态实时刷新    │                 │          │
│  └──────────────────────┘                 │          │
└───────────────────────────────────────────┼──────────┘
                                            │ UDP JSON
                                            ▼
                              ┌──────────────────────┐
                              │   D-BOT (ESP32-S3)    │
                              │                       │
                              │  UDPComm (port 6090)  │
                              │       ▼               │
                              │  DBot::handleMessage  │
                              │  - MOVE / SPIN        │
                              │  - STOP / EMERGENCY   │
                              │       ▼               │
                              │  命令队列 + PID 控制   │
                              │       ▼               │
                              │  SimpleFOC 电机驱动    │
                              │                       │
                              │  ACK 回执 (UDP 回传)   │
                              └──────────────────────┘
```

### 关键模块说明

| 模块 | 位置 | 说明 |
|------|------|------|
| DBotThing | `py-xiaozhi-main/src/iot/things/dbot.py` | 将 D-BOT 注册为 py-xiaozhi 的 IoT Thing，定义 18 个属性和 16+ 个方法 |
| DBotClient | `py-xiaozhi-main/src/iot/things/dbot_client.py` | UDP 通信客户端，支持 fire-and-forget 和 ACK 两种模式 |
| ThingManager | `py-xiaozhi-main/src/iot/thing_manager.py` | Thing 管理器，路由 AI 语音指令到对应设备 |
| IoT Plugin | `py-xiaozhi-main/src/plugins/iot.py` | IoT 插件，在协议连接时发送设备描述符和状态 |
| D-BOT Bot | `D-BOT/src/app/bot/bot.cpp` | ESP32 端核心逻辑，处理命令队列、PID 控制、ACK 发送 |
| UDPComm | `D-BOT/src/app/bot/comm/udp_comm.cpp` | ESP32 端 UDP 通信层 |

## 五、开发阶段

### 阶段一：py-xiaozhi PC 客户端复现

**目标**：在 Linux PC 上成功运行 py-xiaozhi，实现基础语音交互能力。

**完成内容**：
- 搭建 Python 虚拟环境（Conda），安装全部依赖（sounddevice、opuslib、PyQt5、sherpa-onnx 等）
- 配置音频设备（输入/输出），解决 PipeWire/ALSA 桥接问题
- 配置 Fcitx5 输入法兼容性
- 成功运行 py-xiaozhi GUI 模式，实现语音唤醒和 AI 对话
- 熟悉 py-xiaozhi 的插件架构和 IoT Thing 机制

### 阶段二：D-BOT Thing 接入

**目标**：将 D-BOT 注册为 py-xiaozhi 的 IoT Thing，实现通过语音指令控制机器人。

**完成内容**：
- 实现 `DBotClient` 类：基于 UDP Socket 的通信客户端，支持 JSON 指令发送
- 实现 `DBotThing` 类：注册为标准 Thing，定义属性（online、busy、robot_status 等）和方法（Move、Spin、Stop 等）
- 实现方向语义映射：MoveForward/MoveBackward/TurnLeft/TurnRight 通过 `FORWARD_MOVE_POSITIVE` 和 `LEFT_SPIN_POSITIVE` 配置适配不同安装方向
- 实现动作组合：RunSequence（通用动作序列）、SquarePatrol（走正方形）、DemoDance（演示动作）
- 实现高层语义方法：GoForwardALittle、GoBackwardALittle、TurnLeftALittle、TurnRightALittle、TurnAround、PerformDemo
- 在 `config.json` 中添加 DBOT 配置段
- 在 IoT Plugin 中自动注册 D-BOT Thing

### 阶段三：D-BOT 固件增强 — STOP / EMERGENCY_STOP / ACK

**目标**：增强 D-BOT 固件，支持命令中断和执行状态回执。

**完成内容**：
- **命令类型扩展**：在 `CommandType` 枚举中新增 `STOP` 和 `EMERGENCY_STOP`
- **命令队列**：使用 FreeRTOS 互斥锁保护的 `commandQueue`，支持命令排队执行
- **STOP 实现**：清空命令队列 + 设置 `stop_flag_` + 立即停止电机
- **EMERGENCY_STOP 实现**：与 STOP 相同的清队列和停止逻辑（预留未来扩展区分）
- **ACK 回执协议**：
  - 命令到达时立即发送 `stage: "received"` ACK
  - 命令开始执行时发送 `stage: "started"` ACK
  - 命令完成时发送 `stage: "completed"` ACK 或 `stage: "failed"` ACK
  - ACK JSON 包含 `cmd_id`、`action`、`stage`、`status`、`message` 字段
- **向后兼容**：未设置 `expect_ack` 字段的旧版指令不发送 ACK，保持兼容

### 阶段四：PC 端 ACK 适配、GUI 增强、动作组合、高层语义

**目标**：在 PC 端完整适配 ACK 机制，增强 GUI 展示，实现组合动作和高层语义控制。

**完成内容**：
- **DBotClient ACK 模式**：
  - 实现 `_AckProtocol`（asyncio DatagramProtocol），在 `ack_listen_port` 上监听 ACK 回执
  - 通过 `cmd_id` 匹配等待中的 Future，实现异步等待
  - 支持超时处理和异常捕获
  - 懒启动 ACK 监听器，避免端口占用
- **DBotThing ACK 状态属性**：新增 `ack_enabled`、`last_command_id`、`last_ack_stage`、`last_ack_message`、`last_ack_raw`、`last_ack_time` 等属性
- **D-BOT 控制面板**（`dbot_panel.py`）：
  - 实时显示 D-BOT 状态（在线/忙碌/机器人状态/ACK 信息）
  - 手动控制按钮：前进、后退、左转、右转、掉头、Ping、停止、急停
  - 动作组合按钮：走正方形、演示动作
  - 1 秒自动刷新定时器
- **测试脚本**：
  - `D-BOT/tools/test_udp_ack.py`：ESP32 端 UDP ACK 测试（7 个测试场景）
  - `py-xiaozhi-main/scripts/test_dbot_thing.py`：Thing 层手动测试
  - `py-xiaozhi-main/scripts/test_dbot_ack.py`：Thing 层 ACK 完整测试

## 六、运行环境

### 6.1 硬件要求

| 组件 | 说明 |
|------|------|
| D-BOT 机器人 | ESP32-S3 + SimpleFOC 无刷电机 + MPU6050/BMI270 IMU |
| Linux PC | Ubuntu 24.04（推荐），需有麦克风和扬声器 |
| WiFi 路由器 | PC 和 D-BOT 需在同一局域网 |

### 6.2 软件依赖

**PC 端（py-xiaozhi）**：
- Python 3.10+（推荐使用 Conda 虚拟环境）
- 依赖包见 `py-xiaozhi-main/requirements.txt`，主要包括：
  - `PyQt5`：GUI 框架
  - `sounddevice`：音频采集
  - `opuslib`：Opus 编解码
  - `websockets`：WebSocket 协议
  - `sherpa-onnx`：语音唤醒模型推理
  - `qasync`：Qt 异步事件循环

**D-BOT 固件端**：
- PlatformIO（VSCode 插件或 CLI）
- ESP32-S3 开发板支持包
- 依赖库见 `D-BOT/platformio.ini`：SimpleFOC、ArduinoJson、WiFiManager 等

### 6.3 网络配置

- D-BOT 连接 WiFi 后获取 IP 地址（通过串口或 WiFiManager 查看）
- PC 端 `config.json` 中 `DBOT.IP_ADDRESS` 设置为 D-BOT 的 IP
- D-BOT 监听 UDP 6090 端口
- PC 端监听 UDP 16090 端口接收 ACK 回执

## 七、运行方法

### 7.1 D-BOT 固件烧录

```bash
cd D-BOT

# 编译（根据硬件版本选择环境）
pio run -e D-BOT-v1_0    # v1.0 硬件（BMI270）
pio run -e D-BOT-v0_1    # v0.1 硬件（MPU6050）

# 烧录
pio run -e D-BOT-v1_0 --target upload
```

### 7.2 py-xiaozhi 启动

```bash
cd py-xiaozhi-main

# 方式一：使用启动脚本（推荐，已配置环境变量）
bash start_xiaozhi.sh

# 方式二：手动启动
conda activate py-xiaozhi
python main.py --mode gui --protocol websocket

# CLI 模式
python main.py --mode cli
```

### 7.3 配置 D-BOT IP

编辑 `py-xiaozhi-main/config/config.json`，修改 `DBOT` 段：

```json
{
  "DBOT": {
    "ENABLED": true,
    "IP_ADDRESS": "192.168.1.117",
    "PORT": 6090,
    "EXPECT_ACK": true,
    "ACK_TIMEOUT_SEC": 10.0,
    "ACK_LISTEN_PORT": 16090
  }
}
```

## 八、测试方法

### 8.1 D-BOT 固件端 UDP ACK 测试

```bash
cd D-BOT
python3 tools/test_udp_ack.py <D-BOT的IP地址>
```

该脚本包含 7 个测试场景：
1. MOVE 带 ACK → 验证 received + started + completed 三阶段回执
2. SPIN 带 ACK → 验证旋转命令三阶段回执
3. STOP 中断 MOVE → 验证正在执行的命令被中断
4. EMERGENCY_STOP 中断 SPIN → 验证急停功能
5. 不支持的 action → 验证返回 failed ACK
6. MOVE 不带 ACK → 验证向后兼容（无回复）
7. STOP 清空队列 → 验证队列中的后续命令不被执行

### 8.2 PC 端 Thing 层 ACK 测试

```bash
cd py-xiaozhi-main
PYTHONPATH=. python scripts/test_dbot_ack.py --ping
PYTHONPATH=. python scripts/test_dbot_ack.py --move 10
PYTHONPATH=. python scripts/test_dbot_ack.py --spin -90
PYTHONPATH=. python scripts/test_dbot_ack.py --stop
PYTHONPATH=. python scripts/test_dbot_ack.py --square
PYTHONPATH=. python scripts/test_dbot_ack.py --demo
```

### 8.3 PC 端 Thing 层手动测试

```bash
cd py-xiaozhi-main
PYTHONPATH=. python scripts/test_dbot_thing.py
```

## 九、演示流程

以下为 3-5 分钟演示视频的建议流程：

1. **开场介绍**（30 秒）：介绍项目背景和目标
2. **系统启动**（30 秒）：展示 py-xiaozhi GUI 启动，D-BOT 面板显示在线状态
3. **语音控制**（60 秒）：通过语音指令控制 D-BOT 前进、后退、旋转
4. **GUI 手动控制与 ACK 展示**（60 秒）：通过 GUI 按钮控制机器人，展示 ACK 状态实时更新
5. **STOP / 急停**（30 秒）：演示正在运动时发送 STOP 或 EmergencyStop
6. **走正方形 / 演示动作**（30 秒）：展示动作组合功能
7. **总结**（30 秒）：回顾项目成果

详见 `docs/demo_script.md`。

## 十、已知限制

1. **定位与导航**：当前系统不具备自主定位、视觉导航或路径规划能力。机器人的运动为开环控制（基于编码器和 IMU 的 PID），不涉及 SLAM 或地图构建。
2. **运动精度**：D-BOT 为桌面平衡机器人，受限于轮径和 IMU 精度，移动距离和旋转角度存在累积误差。
3. **通信可靠性**：基于 UDP 协议，不保证数据包到达。ACK 机制可以检测超时，但不提供重传。
4. **语音识别依赖云端**：语音识别和 AI 对话依赖小智云端服务（api.tenclass.net），需要网络连接。
5. **单机器人控制**：当前架构支持控制一台 D-BOT，多机器人控制需要扩展 Thing 注册逻辑。
6. **音频回声消除**：AEC（回声消除）功能默认关闭，开启后可能影响语音识别效果。
7. **硬件依赖**：D-BOT 需要特定硬件（ESP32-S3 + SimpleFOC 驱动板 + 无刷电机 + IMU），无法纯软件模拟。

## 十一、总结

本项目通过复现 py-xiaozhi 并将其与 D-BOT 开源项目对接，实现了以下目标：

1. **小智硬件的软件替代**：在 Linux PC 上实现了完整的语音交互流程（唤醒 → 识别 → AI 对话 → 设备控制），无需小智 AI 专用硬件。
2. **IoT Thing 机制复用**：沿用 py-xiaozhi 的 Thing 抽象层，将 D-BOT 注册为标准 IoT 设备，使 AI 语音助手能够自动发现和调用机器人的方法。
3. **ACK 闭环机制**：在 D-BOT 固件端实现了三阶段 ACK 回执（received → started → completed/failed），PC 端通过异步 UDP 监听实现可靠的命令-响应闭环。
4. **安全控制**：实现了 STOP 和 EMERGENCY_STOP 指令，支持正在执行的命令中断、命令队列清空和电机立即停止。
5. **动作组合与高层语义**：实现了 RunSequence 通用动作序列、SquarePatrol 走正方形、DemoDance 演示动作，以及 GoForwardALittle、TurnAround 等高层语义方法，使语音控制更加自然。
6. **GUI 增强**：在 py-xiaozhi 的 GUI 中添加了 D-BOT 控制面板，实时显示机器人状态、ACK 信息，提供手动控制和动作组合按钮。

本项目的核心贡献在于建立了从"语音输入 → AI 理解 → IoT Thing 调用 → UDP 指令 → ACK 回执 → 状态展示"的完整链路，验证了 py-xiaozhi 作为小智硬件替代方案控制物理机器人（D-BOT）的可行性。
