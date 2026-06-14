#include "Account_Master.h"
#include "hal/hal.h"
#include "app/Configs/Config.h"

using namespace AccountSystem;

static int onEvent(Account* account, Account::EventParam_t* param)
{
    if (param->event != Account::EVENT_NOTIFY)
    {
        return Account::ERROR_UNSUPPORTED_REQUEST;
    }

    if (param->size != sizeof(AccountSystem::Motor_Info_t))
    {
        return Account::ERROR_SIZE_MISMATCH;
    }

    AccountSystem::Motor_Info_t* info = (AccountSystem::Motor_Info_t*)param->data_p;
    log_e("Motor: OnEvent");
    switch (info->cmd)
    {
    case MOTOR_CMD_CHANGE_MODE:
        /* code */
        HAL::update_motor_mode(info->motor_num, info->motor_mode, info->init_position);
        HAL::motor_shake(info->motor_num, 2, 2);
        break;
    case MOTOR_CMD_CHECKOUT_PAGE:
        HAL::motor_shake(info->motor_num, 2, 2);
        break;
    default:
        break;
    }
    

    return 0;
}

ACCOUNT_INIT_DEF(Motor)
{
    account->SetEventCallback(onEvent);
}