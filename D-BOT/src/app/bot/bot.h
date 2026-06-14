/**
  *   Copyright (C) 2025 dingmos. All rights reserved.
  * @file    bot.h
  * @author  dingmos
  * @version V0.1.0
  * @date    2025-02-23
  * @brief   Bot 状态控制
*/
#ifndef __BOT_H__
#define __BOT_H__

#include <iostream>
#include <vector>
#include <memory>
#include <string>

#include <SimpleFOC.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "comm/simple_comm.h"

enum bot_control_type {
    BOT_CONTROL_TYPE_AI,
    BOT_CONTROL_TYPE_JOYSTICKS,
    BOT_CONTROL_TYPE_MAX,
};

extern int g_bot_ctrl_type;

enum class CommandType {
    SPIN,
    MOVE,
    STOP,
    EMERGENCY_STOP
};

enum class CommandStatus {
    PENDING,   
    EXECUTING,  
    COMPLETED,  
    FAILED
};

struct Command {
    CommandType type;
    double value;
    CommandStatus status;
    double target_value;
    std::string cmd_id;
    bool expect_ack;
    iot::SimpleComm* sender_comm;
};

class DBot {
public:
    DBot() : queue_mutex_(xSemaphoreCreateMutex()), stop_flag_(false) {};

    // 删除拷贝构造函数和赋值运算符
    DBot(const DBot&) = delete;
    DBot& operator=(const DBot&) = delete;

    // 工厂函数，返回 DBot 的单例实例
    static DBot& getInstance();

    void init();

    void addComm(iot::SimpleComm *comm);
    void loop();
    void spin(double angel);
    void move(double distance);

    int spinExe(double angel);
    int moveExe(double angel);
    bool hasCmd(void);
    Command popCommand(void);
    int setTargetValue(Command& cmd, double target);
    int cmdExe(const Command &cmd, double cur);

    // Called by dbot_thread to handle one command cycle (pop, execute, ACK)
    void runCommandCycle(void);
    // Check and consume stop flag
    bool checkAndClearStop(void);
    void sendAck(iot::SimpleComm* comm, const std::string& cmd_id,
                 const char* action, const char* stage,
                 const char* status, const char* message = nullptr);

private:
    double distanceToAngel(double distance);
    std::vector<Command> commandQueue;
    SemaphoreHandle_t queue_mutex_;
    volatile bool stop_flag_;
    double target_yaw;
    void handleMessage(const JsonDocument& json, iot::SimpleComm* sender);
    void handleStop(const JsonDocument& json, iot::SimpleComm* sender, bool emergency);
    std::vector<iot::SimpleComm *> _comms;
};

#endif 