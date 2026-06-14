#ifndef __ESPNOW_COMM_H__
#define __ESPNOW_COMM_H__

#include "simple_comm.h"
#include <esp_now.h>
#include <WiFi.h>

namespace iot {

class ESPNOWComm : public SimpleComm {
public:
    ESPNOWComm();
    int Init() override;
    int Send(const JsonDocument& json) override;
    void SetRecvCallback(RecvCallback callback) override;
    void SetPeerAddress(const uint8_t* macAddress);
    void Loop() override;

private:
    static ESPNOWComm* activeInstance;

    static void OnDataReceived(const uint8_t* mac, const uint8_t* data, int len){

        log_i("receved msg from %s\n", mac);
        if (activeInstance->recv_cb_) {
            JsonDocument doc;
            DeserializationError error = deserializeJson(doc, data, len);
            if (!error) {
                activeInstance->recv_cb_(doc, activeInstance);
            }
        }
    }

    uint8_t _peerAddress[6];
    RecvCallback recv_cb_;
};

} // namespace iot

#endif