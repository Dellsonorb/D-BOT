/**
  *   Copyright (C) 2025 dingmos. All rights reserved.
  * @file    bot.c
  * @author  dingmos
  * @version V0.1.0
  * @date    2025-02-23
  * @brief   Bot 状态控制
*/
#include "bot.h"
#include "hal/hal.h"

int g_bot_ctrl_type = BOT_CONTROL_TYPE_AI;

#define WHEEL_DIAMETER 6
#define WHEEL_CIRCUMFERENCE (WHEEL_DIAMETER * M_PI)
#define BOT_MOVE_END_OFFSET (30)
#define BOT_SPIN_END_OFFSET (10)
#define BOT_ACTION_END_TIME (200)
PIDController pid_bot_s {
    .P = 6, .I = 0, .D = 2, .ramp = 100000, 
    .limit = BOT_MAX_STEERING
};

#ifdef D_BOT_HW_V1
PIDController pid_bot_m {
    .P = 0.03, .I = 0, .D = 0.01, .ramp = 100000, 
    .limit = MOTOR_MAX_SPEED
}; 
#else

PIDController pid_bot_m {
    .P = 0.03, .I = 0, .D = 0.027, .ramp = 100000, 
    .limit = MOTOR_MAX_SPEED
}; 

#endif
static int execute_cmd(Command& cmd) 
{
    int rc = 0;
    float abs_yaw = 0;
    float cur = 0;
    DBot &dbot = DBot::getInstance();
    switch (cmd.type) {
        case CommandType::SPIN:
            abs_yaw = HAL::imu_get_abs_yaw();
#ifdef D_BOT_HW_V1
            dbot.setTargetValue(cmd, abs_yaw - cmd.value);
#else
             // actual yaw need to be x2
            dbot.setTargetValue(cmd, abs_yaw - cmd.value *2);
#endif
           
            cmd.status = CommandStatus::EXECUTING;
            cur = abs_yaw;
            break;
        case CommandType::MOVE:
            cur = HAL::motor_get_cur_angle();
            // log_e("move set target: %lf, cur: %lf.", cmd.value + cur, cur);
            dbot.setTargetValue(cmd, cur - cmd.value);
            cmd.status = CommandStatus::EXECUTING;
            break;
    }

    rc = dbot.cmdExe(cmd, cur);
    if (rc == 0) {
        cmd.status = CommandStatus::COMPLETED;
    }
    return rc;
}

void dbot_loop_thread(void* argument)
{
    DBot &dbot = DBot::getInstance();
    while(1) {
        dbot.loop();
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void dbot_thread(void* argument)
{
    DBot &dbot = DBot::getInstance();
    while(1) {
        if (dbot.hasCmd()) {
            dbot.runCommandCycle();
        } else {
            vTaskDelay(pdMS_TO_TICKS(50));
        }
    }
}

DBot& DBot::getInstance() {
    // std::unique_ptr<DBot> DBot::_instance
    static auto instance = std::unique_ptr<DBot>(new DBot());
    return *instance;
}

void DBot::addComm(iot::SimpleComm *comm) {
    _comms.push_back(comm);
}

void DBot::init(void)
{
    for (auto& comm : _comms) {
        // ESP_ERROR_CHECK(comm->Init());
        comm->SetRecvCallback([this](const JsonDocument& json, iot::SimpleComm* sender) {
            handleMessage(json, sender);
        });
    }
    TaskHandle_t handleXBotThread;
    xTaskCreate(
        dbot_thread,
        "DBotThread",
        4096,
        nullptr,
        ESP32_RUNNING_CORE,
        &handleXBotThread);
    TaskHandle_t handleDBotLoop;
    xTaskCreate(
        dbot_loop_thread,
        "DBotLoop",
        4096,
        nullptr,
        ESP32_RUNNING_CORE,
        &handleDBotLoop);
}

void DBot::handleMessage(const JsonDocument& json, iot::SimpleComm* sender) {
    const char* action = json["action"];
    if (!action) {
        log_w("handleMessage: missing action field");
        return;
    }

    double target = json["target"] | 0.0;
    bool expect_ack = json["expect_ack"] | false;
    const char* cmd_id_str = json["cmd_id"] | "";
    std::string cmd_id(cmd_id_str);

    log_i("action %s, target %.2lf, expect_ack %d, cmd_id %s\n",
          action, target, expect_ack, cmd_id.c_str());

    if (strcmp(action, "STOP") == 0 || strcmp(action, "EMERGENCY_STOP") == 0) {
        handleStop(json, sender, strcmp(action, "EMERGENCY_STOP") == 0);
    } else if (strcmp(action, "MOVE") == 0 || strcmp(action, "SPIN") == 0) {
        // Send "received" ACK immediately
        if (expect_ack) {
            sendAck(sender, cmd_id, action, "received", "success");
        }

        CommandType type = (strcmp(action, "MOVE") == 0) ? CommandType::MOVE : CommandType::SPIN;
        double value;
        if (type == CommandType::MOVE) {
            value = distanceToAngel(target);
        } else {
            value = target;
        }

        Command cmd;
        cmd.type = type;
        cmd.value = value;
        cmd.status = CommandStatus::PENDING;
        cmd.target_value = 0;
        cmd.cmd_id = cmd_id;
        cmd.expect_ack = expect_ack;
        cmd.sender_comm = sender;

        xSemaphoreTake(queue_mutex_, portMAX_DELAY);
        commandQueue.push_back(cmd);
        xSemaphoreGive(queue_mutex_);
    } else {
        log_w("handleMessage: unknown action '%s'", action);
        if (expect_ack) {
            sendAck(sender, cmd_id, action, "failed", "error", "unsupported action");
        }
    }
}

void DBot::handleStop(const JsonDocument& json, iot::SimpleComm* sender, bool emergency) {
    const char* action_str = emergency ? "EMERGENCY_STOP" : "STOP";
    bool expect_ack = json["expect_ack"] | false;
    const char* cmd_id_str = json["cmd_id"] | "";
    std::string cmd_id(cmd_id_str);

    log_i("handleStop: %s, expect_ack %d", action_str, expect_ack);

    if (expect_ack) {
        sendAck(sender, cmd_id, action_str, "received", "success");
    }

    // Clear command queue under mutex
    xSemaphoreTake(queue_mutex_, portMAX_DELAY);
    commandQueue.clear();
    xSemaphoreGive(queue_mutex_);

    // Signal executing thread to stop
    stop_flag_ = true;

    // Immediately stop motors
    HAL::motor_set_speed(0, 0);

    log_i("handleStop: motors stopped, queue cleared");

    if (expect_ack) {
        sendAck(sender, cmd_id, action_str, "completed", "success");
    }
}

void DBot::sendAck(iot::SimpleComm* comm, const std::string& cmd_id,
                   const char* action, const char* stage,
                   const char* status, const char* message) {
    if (!comm) {
        log_w("sendAck: comm is null, cmd_id=%s stage=%s", cmd_id.c_str(), stage);
        return;
    }

    JsonDocument doc;
    doc["cmd_id"] = cmd_id;
    doc["action"] = action;
    doc["stage"] = stage;
    doc["status"] = status;
    if (message) {
        doc["message"] = message;
    }

    log_i("ACK >>> cmd_id=%s action=%s stage=%s status=%s",
          cmd_id.c_str(), action, stage, status);
    comm->Send(doc);
}

void DBot::loop() {
    for (auto& comm : _comms) {
        comm->Loop();
    }
}

int DBot::setTargetValue(Command& cmd, double target)
{
    if (cmd.status != CommandStatus::PENDING) {
        return -1;
    }
    log_i("set target: %lf, CUR MOTOR angle %lf, bot angle %lf.\n", target, 
                HAL::motor_get_cur_angle(), HAL::imu_get_abs_yaw());
    cmd.target_value = target;
    return 0;
}

int DBot::cmdExe(const Command &cmd, double cur)
{
    float speed = 0, steering = 0;
    float end_offset = 0;
    bool done = false;
    static uint64_t end_time = 0;

    switch (cmd.type) {
        case CommandType::SPIN:
            steering = pid_bot_s(cur - cmd.target_value);
            end_offset = BOT_SPIN_END_OFFSET;
            break;
        case CommandType::MOVE:
            speed = pid_bot_m(cmd.target_value - cur);;
            end_offset = BOT_MOVE_END_OFFSET;
            break;
    }
    
    // Tmp cmd end condition
    if (abs(cmd.target_value - cur) > end_offset) {
        end_time = millis();
    }
    // wireless.printf("target: %.2f current %.2f, output: %.2f, %.2f.\n", 
    //             cmd.target_value, cur, steering, speed);
    if (millis() > end_time + BOT_ACTION_END_TIME) {
        done = true;
        speed = 0;
        steering = 0;
    }

    HAL::motor_set_speed(speed, steering);
    if (done) {
        return 0;
    }
    return -1;
}

void DBot::spin(double angel)
{
    Command cmd;
    cmd.type = CommandType::SPIN;
    cmd.value = angel;
    cmd.status = CommandStatus::PENDING;
    cmd.target_value = 0;
    cmd.expect_ack = false;
    cmd.sender_comm = nullptr;
    xSemaphoreTake(queue_mutex_, portMAX_DELAY);
    commandQueue.push_back(cmd);
    xSemaphoreGive(queue_mutex_);
}

void DBot::move(double distance)
{
    double motor_angle = distanceToAngel(distance);
    Command cmd;
    cmd.type = CommandType::MOVE;
    cmd.value = motor_angle;
    cmd.status = CommandStatus::PENDING;
    cmd.target_value = 0;
    cmd.expect_ack = false;
    cmd.sender_comm = nullptr;
    xSemaphoreTake(queue_mutex_, portMAX_DELAY);
    commandQueue.push_back(cmd);
    xSemaphoreGive(queue_mutex_);
}

double DBot::distanceToAngel(double distance)
{
    return distance/WHEEL_CIRCUMFERENCE*360.0;
}

bool DBot::hasCmd(void)
{
    xSemaphoreTake(queue_mutex_, portMAX_DELAY);
    bool result = !commandQueue.empty();
    xSemaphoreGive(queue_mutex_);
    return result;
}

Command DBot::popCommand(void)
{
    xSemaphoreTake(queue_mutex_, portMAX_DELAY);
    Command cmd = commandQueue.front();
    commandQueue.erase(commandQueue.begin());
    xSemaphoreGive(queue_mutex_);
    return cmd;
}

bool DBot::checkAndClearStop(void)
{
    if (stop_flag_) {
        stop_flag_ = false;
        return true;
    }
    return false;
}

void DBot::runCommandCycle(void)
{
    int rc = 0;
    Command cmd = popCommand();

    // Send "started" ACK if requested
    if (cmd.expect_ack) {
        const char* action_str = (cmd.type == CommandType::SPIN) ? "SPIN" : "MOVE";
        sendAck(cmd.sender_comm, cmd.cmd_id, action_str, "started", "success");
    }

    HAL::audio_play_music("DeviceInsert");
    pid_bot_s.reset();
    pid_bot_m.reset();
    stop_flag_ = false;

    while (cmd.status != CommandStatus::COMPLETED) {
        if (checkAndClearStop()) {
            HAL::motor_set_speed(0, 0);
            cmd.status = CommandStatus::FAILED;
            log_i("command interrupted by stop");
            break;
        }
        rc = execute_cmd(cmd);
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    HAL::audio_play_music("DevicePullout");

    // Send completion ACK if requested
    if (cmd.expect_ack) {
        const char* action_str = (cmd.type == CommandType::SPIN) ? "SPIN" : "MOVE";
        if (cmd.status == CommandStatus::COMPLETED) {
            sendAck(cmd.sender_comm, cmd.cmd_id, action_str, "completed", "success");
        } else {
            sendAck(cmd.sender_comm, cmd.cmd_id, action_str, "failed", "error", "stopped");
        }
    }
}