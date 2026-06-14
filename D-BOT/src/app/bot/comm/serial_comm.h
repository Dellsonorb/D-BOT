#ifndef __SERIAL_COMM_H__
#define __SERIAL_COMM_H__

#include "simple_comm.h"
#include <HardwareSerial.h>

namespace iot {

class SerialComm : public SimpleComm {
public:
    explicit SerialComm(HardwareSerial& serial, unsigned long baudRate = 9600);
    int Init() override;
    int Send(const JsonDocument& json) override;
    void SetRecvCallback(RecvCallback callback) override;
    void Loop() override;

private:
    HardwareSerial& _serial;
    unsigned long _baudRate;
    RecvCallback _recvCallback;
};

} // namespace iot

#endif