#include "Account_Master.h"
#include "hal/hal.h"

static Account* actIMU;

void AccountSystem::imu_commit(HAL::imu_info_t* info)
{
    actIMU->Commit(info, sizeof(HAL::imu_info_t));
}

ACCOUNT_INIT_DEF(IMU)
{
    actIMU = account;
}
