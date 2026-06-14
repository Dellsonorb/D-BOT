#include "serial_comm.h"

namespace iot {

SerialComm::SerialComm(HardwareSerial& serial, unsigned long baudRate)
    : _serial(serial), _baudRate(baudRate) {}

int SerialComm::Init() {
    _serial.begin(_baudRate);
    return 0;
}

int SerialComm::Send(const JsonDocument& json) {
    String output;
    serializeJson(json, output);
    _serial.println(output);
    return 0;
}

void SerialComm::SetRecvCallback(RecvCallback callback) {
    _recvCallback = callback;
}

void SerialComm::Loop() {
    if (_recvCallback && _serial.available()) {
        String input = _serial.readStringUntil('\n');
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, input);
        if (!error) {
            _recvCallback(doc, this);
        }
    }
}

} // namespace iot