#ifndef __SIMPLE_COMM_H__
#define __SIMPLE_COMM_H__

#include <Arduino.h>
#include <ArduinoJson.h>

namespace iot {

class SimpleComm {
public:

    using RecvCallback = std::function<void(const JsonDocument&, SimpleComm* sender)>;

    virtual ~SimpleComm() = default;
    virtual int Init() = 0;
    virtual int Send(const JsonDocument& json) = 0;
    virtual void SetRecvCallback(RecvCallback callback) = 0;
    virtual void Loop() = 0;
};


} // namespace iot

#endif