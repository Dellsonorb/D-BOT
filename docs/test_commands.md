# 测试命令手册

本文档整理了项目中所有测试相关的命令，方便快速验证各模块功能。

---

## 1. py-xiaozhi 启动命令

### 1.1 GUI 模式启动（推荐）

```bash
cd ~/Project/py-xiaozhi-main
bash start_xiaozhi.sh
```

或手动启动：

```bash
cd ~/Project/py-xiaozhi-main
conda activate py-xiaozhi
python main.py --mode gui --protocol websocket
```

### 1.2 CLI 模式启动

```bash
cd ~/Project/py-xiaozhi-main
conda activate py-xiaozhi
python main.py --mode cli
```

### 1.3 跳过设备激活启动

```bash
python main.py --mode gui --skip-activation
```

---

## 2. D-BOT Thing 测试命令

以下命令在 `py-xiaozhi-main` 目录下执行，需要设置 `PYTHONPATH`。

### 2.1 Thing 手动测试脚本

```bash
cd ~/Project/py-xiaozhi-main
PYTHONPATH=. python scripts/test_dbot_thing.py
```

该脚本通过 ThingManager 直接调用 D-BOT 的各种方法，用于验证 Thing 注册和基本通信。

### 2.2 Thing 属性与描述符查看

```bash
cd ~/Project/py-xiaozhi-main

# 查看所有 Thing 描述符（属性和方法定义）
PYTHONPATH=. python scripts/test_dbot_ack.py --descriptors

# 查看所有 Thing 当前状态
PYTHONPATH=. python scripts/test_dbot_ack.py --states
```

### 2.3 Ping 连通性测试

```bash
PYTHONPATH=. python scripts/test_dbot_ack.py --ping
```

---

## 3. ACK 测试命令

### 3.1 PC 端 ACK 测试（通过 ThingManager）

```bash
cd ~/Project/py-xiaozhi-main

# 前进 10 cm（带 ACK）
PYTHONPATH=. python scripts/test_dbot_ack.py --move 10

# 旋转 -90°（带 ACK）
PYTHONPATH=. python scripts/test_dbot_ack.py --spin -90

# 停止
PYTHONPATH=. python scripts/test_dbot_ack.py --stop

# 紧急停止
PYTHONPATH=. python scripts/test_dbot_ack.py --emergency-stop

# 指定前进/后退/左转/右转距离
PYTHONPATH=. python scripts/test_dbot_ack.py --forward 15
PYTHONPATH=. python scripts/test_dbot_ack.py --backward 10
PYTHONPATH=. python scripts/test_dbot_ack.py --left 45
PYTHONPATH=. python scripts/test_dbot_ack.py --right 30

# 高层语义方法
PYTHONPATH=. python scripts/test_dbot_ack.py --go-forward
PYTHONPATH=. python scripts/test_dbot_ack.py --go-backward
PYTHONPATH=. python scripts/test_dbot_ack.py --turn-left
PYTHONPATH=. python scripts/test_dbot_ack.py --turn-right
PYTHONPATH=. python scripts/test_dbot_ack.py --turn-around

# 显示调试日志
PYTHONPATH=. python scripts/test_dbot_ack.py --ping -v
```

### 3.2 D-BOT 固件端 UDP ACK 测试（直接 UDP 通信）

```bash
cd ~/Project/D-BOT

# 运行全部 7 个测试场景
python3 tools/test_udp_ack.py <D-BOT的IP地址>

# 示例
python3 tools/test_udp_ack.py 192.168.1.117
```

测试场景包括：
1. MOVE 带 ACK → 验证 received + started + completed 三阶段
2. SPIN 带 ACK → 验证旋转三阶段回执
3. STOP 中断 MOVE → 验证正在执行的命令被中断
4. EMERGENCY_STOP 中断 SPIN → 验证急停功能
5. 不支持的 action → 验证返回 failed ACK
6. MOVE 不带 ACK → 验证向后兼容（无回复）
7. STOP 清空队列 → 验证队列中的后续命令不被执行

### 3.3 简单 UDP 测试

```bash
cd ~/Project/D-BOT
python3 tools/test.py
```

---

## 4. 动作组合测试命令

### 4.1 动作序列测试

```bash
cd ~/Project/py-xiaozhi-main

# 预设动作序列（前进10→左转90→前进10→右转90）
PYTHONPATH=. python scripts/test_dbot_ack.py --sequence
```

### 4.2 走正方形测试

```bash
cd ~/Project/py-xiaozhi-main

# 走正方形（默认边长 20cm，转弯 90°）
PYTHONPATH=. python scripts/test_dbot_ack.py --square
```

### 4.3 演示动作测试

```bash
cd ~/Project/py-xiaozhi-main

# 演示动作（前进→后退→左转→右转→左转90→右转90）
PYTHONPATH=. python scripts/test_dbot_ack.py --demo

# PerformDemo（等同于 DemoDance）
PYTHONPATH=. python scripts/test_dbot_ack.py --perform-demo
```

### 4.4 动态修改目标 IP

```bash
cd ~/Project/py-xiaozhi-main
PYTHONPATH=. python scripts/test_dbot_ack.py --set-ip 192.168.1.100
```

---

## 5. PlatformIO 编译和烧录命令

### 5.1 环境说明

D-BOT 有两个硬件版本，对应两个 PlatformIO 环境：

| 环境名 | 硬件版本 | IMU 传感器 |
|--------|----------|-----------|
| `D-BOT-v0_1` | v0.1 | MPU6050 |
| `D-BOT-v1_0` | v1.0 | BMI270 |

### 5.2 编译命令

```bash
cd ~/Project/D-BOT

# 编译 v1.0 硬件版本（BMI270）
pio run -e D-BOT-v1_0

# 编译 v0.1 硬件版本（MPU6050）
pio run -e D-BOT-v0_1
```

### 5.3 烧录命令

```bash
cd ~/Project/D-BOT

# 烧录到 v1.0 硬件
pio run -e D-BOT-v1_0 --target upload

# 烧录到 v0.1 硬件
pio run -e D-BOT-v0_1 --target upload
```

### 5.4 串口监控

```bash
cd ~/Project/D-BOT

# 监控串口输出（查看日志、IP 地址等）
pio device monitor -e D-BOT-v1_0
```

### 5.5 清理编译产物

```bash
cd ~/Project/D-BOT
pio run -e D-BOT-v1_0 --target clean
```

---

## 6. 网络诊断命令

```bash
# 检查 D-BOT 是否在线
ping 192.168.1.117

# 检查 PC 端 ACK 监听端口是否被占用
ss -ulnp | grep 16090

# 检查 D-BOT UDP 端口是否可达
nc -u -z -v 192.168.1.117 6090
```

---

## 7. 配置文件位置

| 文件 | 说明 |
|------|------|
| `py-xiaozhi-main/config/config.json` | py-xiaozhi 主配置（含 DBOT 段） |
| `D-BOT/platformio.ini` | PlatformIO 编译配置 |
| `D-BOT/src/config.h` | D-BOT 固件全局配置 |

### 7.1 DBOT 配置项说明

```jsonc
{
  "DBOT": {
    "ENABLED": true,              // 是否启用 D-BOT Thing
    "IP_ADDRESS": "192.168.1.117", // D-BOT 的 IP 地址
    "PORT": 6090,                 // D-BOT UDP 端口
    "EXPECT_ACK": true,           // 是否启用 ACK 回执
    "ACK_TIMEOUT_SEC": 10.0,      // ACK 等待超时（秒）
    "ACK_LISTEN_PORT": 16090,     // PC 端 ACK 监听端口
    "FORWARD_MOVE_POSITIVE": true,// 正距离 = 前进
    "LEFT_SPIN_POSITIVE": false,  // 正角度 = 右转（取决于安装方向）
    "MAX_DISTANCE_CM": 300.0,     // 最大移动距离限制
    "MAX_ANGLE_DEG": 360.0        // 最大旋转角度限制
  }
}
```
