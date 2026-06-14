#ifndef __EEPROM_H
#define __EEPROM_H


//#include <EEPROM.h>
#include <Preferences.h>
#include "config.h"
#include <SimpleFOC.h>


#define CONFIG_NAMESPACE         "config"
#define INIT_KEY                 "init"
#define FFAT_KEY                 "ffat"
#define LCD_BK_BRIGHTNESS_KEY    "lcd_bk"
#define LCD_BK_TIME_OUT_KEY      "lcd_time"
#define WIFI_SSID_KEY            "wifi_ssid"
#define WIFI_PASSWORD_KEY        "wifi_password"

#define MQTT_CONFIG              "mqtt_config"
#define MQTT_HOST_KEY            "mqtt_host"
#define MQTT_PORT_KEY            "mqtt_port"
#define MQTT_USERNAME_KEY        "mqtt_username"
#define MQTT_PASSWORD_KEY        "mqtt_password"
#define MQTT_TPOIC_PREFIX_KEY    "mqtt_topic_prefix"

#define IMU_CONFIG               "imu_config"
#define IMU_GYRO_X_OFFSET        "xoffset"
#define IMU_GYRO_Y_OFFSET        "yoffset"
#define IMU_GYRO_Z_OFFSET        "zoffset"

#define MOTOR_CONFIG             "motor_config"
#define MOTOR_LEFT_OFFSET        "motor_l_offset"
#define MOTOR_RIGHT_OFFSET       "motor_r_offset"

#define PID_S_CONFIG  "PID_S"
#define PID_V_CONFIG  "PID_V"
#define PID_T_CONFIG  "PID_T"
#define PID_R_CONFIG  "PID_R"
#define PID_B_CONFIG  "PID_B"

#define PID_P_KEY     "pid_p"
#define PID_I_KEY     "pid_i"
#define PID_D_KEY     "pid_d"
#define PID_RAMP_KEY  "pid_ramp"
#define PID_LIMIT_KEY "pid_limit"

#define NVS_D_BOT   "d_bot"
#define MACHINE_MID_VALUE_KEY "mid_value"

#define GAME_CTRLR   "game_ctrlr"
#define GAME_CTRLR_ADDR_KEY "game_ctrlr_addr"

typedef struct {
    bool init_ffat_flag;
    int lcd_bk_timeout;
    int lcd_bk_brightness;
} NvsConfig;


#define MQTT_SERVER   "10.0.0.2"
#define MQTT_PORT     1883
#define MQTT_USER     "mqttuser"
#define MQTT_PASSWORD "mqttpassword"
#define TOPIC_PREFIX  "dingmos"         // owner 

struct mqtt_config {
    String mqtt_host;
    String mqtt_username;
    String mqtt_password;
    int mqtt_port;
    String mqtt_topic_prefix;
};

struct imu_offset {
    float xoffset;
    float yoffset;
    float zoffset;
};

struct motor_offset {
    float l_offset;
    float r_offset;
};

void nvs_init();
uint8_t get_init_ffat();
void set_init_ffat(uint8_t value);
uint16_t get_lcd_bk_brightness();
void set_lcd_bk_brightness(uint16_t value);
uint16_t get_lcd_bk_timeout();
void set_lcd_bk_timeout(uint16_t value);
int nvs_get_mqtt_config(struct mqtt_config *mqtt_conf);
int nvs_set_mqtt_config(String host, uint16_t port, String username, 
                            String password, String topic_prefix);
void set_imu_config(float gyroXoffset, float gyroYoffset, float gyroZoffset);
int get_imu_offset(struct imu_offset *offset);
void nvs_set_motor_config(float motor_l_offset, float motor_r_offset);
int nvs_get_motor_offset(struct motor_offset *offset);

int nvs_set_pid_config(const char *name, PIDController pid);
int nvs_get_pid_config(const char *name, PIDController &pid);
int nvs_set_float(const char *name, const char *key, float vaule);
int nvs_get_float(const char *name, const char *key, float &vaule);

int nvs_set_string(const char *name, const char *key, const char *str);
int nvs_get_string(const char *name, const char *key, char *buf, int len);
#endif