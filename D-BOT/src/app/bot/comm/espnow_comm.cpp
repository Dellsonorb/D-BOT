#include "espnow_comm.h"

namespace iot {


ESPNOWComm *ESPNOWComm::activeInstance = nullptr;

ESPNOWComm::ESPNOWComm() {
    activeInstance = this;  // 构造时绑定实例
    esp_now_register_recv_cb(OnDataReceived);
}

int ESPNOWComm::Init() {
    // WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK) {
        return -1;
    }
    log_i("WiFi channel %d.", WiFi.channel());
    return 0;
}

int ESPNOWComm::Send(const JsonDocument& json) {
    String output;
    serializeJson(json, output);
    esp_now_send(_peerAddress, (uint8_t*)output.c_str(), output.length());
    return 0;
}

void ESPNOWComm::SetRecvCallback(RecvCallback callback) {
    recv_cb_ = callback;
}

void ESPNOWComm::SetPeerAddress(const uint8_t* macAddress) {
    memcpy(_peerAddress, macAddress, 6);
    esp_now_peer_info_t peerInfo;
    memcpy(peerInfo.peer_addr, _peerAddress, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;
    esp_now_add_peer(&peerInfo);
}

void ESPNOWComm::Loop() {
    // ESPNOW 是异步的，不需要在 Loop 中做任何事情
}


} // namespace iot