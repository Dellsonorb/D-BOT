#ifndef __UDP_COMM_H__
#define __UDP_COMM_H__

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <vector>
#include <string>
#include <functional>
#include "simple_comm.h"

namespace iot {

class UDPComm : public SimpleComm{
public:
    UDPComm(const std::string& ssid, const std::string& password, uint16_t localPort);
    ~UDPComm();

    int Init() override;
    int Send(const JsonDocument& json) override;
    void SetRecvCallback(RecvCallback callback) override;
    void Loop();

private:
    std::string ssid_;
    std::string password_;
    uint16_t local_port_;
    WiFiUDP udp_;
    RecvCallback recvCallback_;
    IPAddress last_remote_ip_;
    uint16_t last_remote_port_ = 0;
};

} // namespace iot

#endif // __UDP_COMM_H__