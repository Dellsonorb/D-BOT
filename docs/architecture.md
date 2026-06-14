# 系统架构图

本文档包含三张 Mermaid 架构图，展示系统的整体架构、IoT/Thing 调用流程和 UDP ACK 闭环流程。

---

## 1. 系统总体架构图

```mermaid
graph TB
    subgraph PC["Linux PC 端"]
        MIC["🎤 麦克风<br/>音频输入"]
        SPK["🔊 扬声器<br/>音频输出"]

        subgraph Xiaozhi["py-xiaozhi"]
            APP["Application<br/>设备状态机<br/>IDLE / LISTENING / SPEAKING"]
            PROTO["Protocol 层<br/>WebSocket / MQTT"]
            AUDIO["Audio Plugin<br/>音频采集与播放"]
            WAKE["WakeWord Plugin<br/>语音唤醒<br/>Sherpa-ONNX"]
            IOT_PLUG["IoT Plugin<br/>设备描述符/状态管理"]
            UI["UI Plugin<br/>GUI 渲染"]
            MCP["MCP Plugin<br/>工具调用"]
        end

        subgraph ThingLayer["IoT Thing 层"]
            TM["ThingManager<br/>设备注册与路由"]
            DBOT_THING["DBotThing<br/>18 属性 + 16+ 方法<br/>动作组合 / 高层语义"]
            DBOT_CLI["DBotClient<br/>UDP 通信<br/>ACK 异步等待"]
        end

        subgraph GUI["PyQt5 GUI"]
            MAIN_WIN["主窗口<br/>语音状态 / 表情"]
            DBOT_PANEL["D-BOT 控制面板<br/>状态显示 / 手动控制<br/>ACK 实时刷新"]
        end

        MIC --> AUDIO
        AUDIO --> APP
        APP --> PROTO
        APP --> WAKE
        APP --> IOT_PLUG
        APP --> UI
        APP --> MCP

        IOT_PLUG --> TM
        TM --> DBOT_THING
        DBOT_THING --> DBOT_CLI
        DBOT_CLI -->|"UDP JSON<br/>port 6090"| NET_OUT["网络输出"]
        NET_IN["网络输入<br/>port 16090"] -->|ACK 回执| DBOT_CLI

        UI --> MAIN_WIN
        UI --> DBOT_PANEL
        DBOT_THING -.->|状态查询| DBOT_PANEL

        PROTO -->|"WebSocket<br/>wss://api.tenclass.net"| CLOUD["小智云端<br/>语音识别 + AI 对话"]
        CLOUD -->|IoT 指令| PROTO
    end

    NET_OUT -->|"WiFi / UDP"| DBOT_HW
    DBOT_HW -->|"WiFi / UDP ACK"| NET_IN

    subgraph DBOT_HW["D-BOT 机器人 (ESP32-S3)"]
        UDP["UDPComm<br/>port 6090"]
        BOT["DBot 核心<br/>命令队列<br/>PID 控制"]
        MOTORS["SimpleFOC<br/>无刷电机驱动"]
        IMU["IMU 传感器<br/>MPU6050 / BMI270"]
        ENC["编码器"]
        LCD["GC9A01 LCD<br/>圆形显示屏"]

        UDP --> BOT
        BOT --> MOTORS
        IMU --> BOT
        ENC --> BOT
        BOT --> LCD
    end

    style PC fill:#e3f2fd,stroke:#1565c0
    style Xiaozhi fill:#f3e5f5,stroke:#7b1fa2
    style ThingLayer fill:#fff3e0,stroke:#e65100
    style GUI fill:#e8f5e9,stroke:#2e7d32
    style DBOT_HW fill:#fce4ec,stroke:#c62828
```

---

## 2. IoT/Thing 调用流程图

```mermaid
sequenceDiagram
    participant User as 用户 (语音/GUI)
    participant App as Application
    participant IoT as IoT Plugin
    participant TM as ThingManager
    participant Thing as DBotThing
    participant Client as DBotClient
    participant Bot as D-BOT (ESP32)

    Note over User, Bot: 阶段 1: IoT 设备注册
    App->>IoT: on_protocol_connected()
    IoT->>TM: initialize_iot_devices(config)
    TM->>Thing: new DBotThing(config)
    Thing->>Client: new DBotClient(host, port, ack配置)
    IoT->>TM: get_descriptors_json()
    TM-->>IoT: 设备描述符 (18 属性 + 16+ 方法)
    IoT->>App: send_iot_descriptors(json)
    App->>App: 发送到小智云端

    Note over User, Bot: 阶段 2: 语音指令执行
    User->>App: "向前走"
    App->>App: 语音识别 → AI 理解意图
    App->>IoT: on_incoming_json(IoT指令)
    IoT->>TM: invoke({name:"DBot", method:"MoveForward", params})
    TM->>Thing: invoke(command)
    Thing->>Thing: _execute_motion("MoveForward", "MOVE", target)
    Thing->>Client: send_action("MOVE", target)

    Note over Client, Bot: 阶段 3: UDP 通信 + ACK
    Client->>Client: _ensure_ack_listener()
    Client->>Bot: UDP {cmd_id, action:"MOVE", target, expect_ack:true}
    Bot-->>Client: ACK {stage:"received"}
    Client->>Client: 更新 Future (非终态，继续等待)
    Bot-->>Client: ACK {stage:"started"}
    Client->>Client: 更新 Future (非终态，继续等待)
    Bot-->>Client: ACK {stage:"completed", status:"success"}
    Client->>Client: Future.set_result(ack)

    Note over User, Bot: 阶段 4: 结果返回
    Client-->>Thing: {success:true, stage:"completed"}
    Thing->>Thing: 更新属性 (robot_status, last_result, ack_stage)
    Thing-->>TM: {status:"success", message:"已完成"}
    TM-->>IoT: 执行结果
    IoT->>IoT: get_states_json(delta=true)
    IoT->>App: send_iot_states(delta_states)
    App->>App: 发送状态到云端 + 更新 GUI
```

---

## 3. UDP ACK 闭环流程图

```mermaid
sequenceDiagram
    participant PC as PC (DBotClient)
    participant ESP as D-BOT (ESP32)

    Note over PC, ESP: 完整的 ACK 三阶段闭环

    rect rgb(232, 245, 233)
        Note right of PC: 命令发送
        PC->>PC: 生成 cmd_id (UUID)
        PC->>PC: 创建 Future, 注册到 pending_cmds
        PC->>ESP: UDP {cmd_id, action:"MOVE", target:10.0, expect_ack:true}
    end

    rect rgb(227, 242, 253)
        Note right of PC: 阶段 1: received
        ESP->>ESP: handleMessage() 解析 JSON
        ESP->>ESP: 验证 action 合法
        ESP-->>PC: ACK {cmd_id, action:"MOVE", stage:"received", status:"success"}
        PC->>PC: Future 未完成 (stage != completed/failed)
    end

    rect rgb(255, 243, 224)
        Note right of PC: 阶段 2: started
        ESP->>ESP: runCommandCycle() 从队列取出命令
        ESP->>ESP: PID 控制器初始化
        ESP-->>PC: ACK {cmd_id, action:"MOVE", stage:"started", status:"success"}
        PC->>PC: Future 未完成 (stage != completed/failed)
    end

    rect rgb(232, 245, 233)
        Note right of PC: 执行中
        ESP->>ESP: cmdExe() PID 循环
        ESP->>ESP: HAL::motor_set_speed(speed, steering)
        ESP->>ESP: 检测 stop_flag_ (可能被 STOP 中断)
    end

    rect rgb(227, 242, 253)
        Note right of PC: 阶段 3: completed
        ESP->>ESP: cmd.status == COMPLETED
        ESP-->>PC: ACK {cmd_id, action:"MOVE", stage:"completed", status:"success"}
        PC->>PC: Future.set_result(ack) ← 终态
    end

    PC->>PC: 返回 {success:true, stage:"completed"}
    PC->>PC: 更新 Thing 属性

    Note over PC, ESP: ─── STOP 中断场景 ───

    rect rgb(252, 228, 236)
        Note right of PC: STOP 中断
        PC->>ESP: UDP {cmd_id:"stop-xxx", action:"STOP", expect_ack:true}
        ESP-->>PC: ACK {stage:"received"} (STOP 命令)
        ESP->>ESP: commandQueue.clear()
        ESP->>ESP: stop_flag_ = true
        ESP->>ESP: motor_set_speed(0, 0) 立即停机
        ESP-->>PC: ACK {stage:"completed"} (STOP 命令)
        Note right of ESP: 正在执行的 MOVE 命令
        ESP->>ESP: checkAndClearStop() → true
        ESP->>ESP: cmd.status = FAILED
        ESP-->>PC: ACK {stage:"failed", status:"error", message:"stopped"}
    end
```

---

## 附：ACK JSON 格式参考

### PC → D-BOT（命令）

```json
{
  "cmd_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "MOVE",
  "target": 10.0,
  "expect_ack": true
}
```

### D-BOT → PC（ACK 回执）

```json
{
  "cmd_id": "550e8400-e29b-41d4-a716-446655440000",
  "action": "MOVE",
  "stage": "completed",
  "status": "success"
}
```

### ACK 阶段说明

| stage | 含义 | 触发时机 |
|-------|------|----------|
| `received` | 命令已收到 | `handleMessage()` 解析 JSON 后立即发送 |
| `started` | 命令开始执行 | `runCommandCycle()` 从队列取出命令后 |
| `completed` | 命令执行完成 | `cmd.status == COMPLETED` |
| `failed` | 命令执行失败 | 被 STOP 中断或执行异常 |
