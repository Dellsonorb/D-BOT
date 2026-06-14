/**
  * @file    controller.h
  * @author  dingmos
  * @version V0.0.1
  * @date    2025-02-16
  * @brief   结合 button 库解析遥控器状态。
*/

#ifndef __CONTROLLER_H__
#define __CONTROLLER_H__
#define DEFAULTU_BLE_ADDR "04:0A:11:11:90:10"
void controller_init(const char *ble_addr);

#endif