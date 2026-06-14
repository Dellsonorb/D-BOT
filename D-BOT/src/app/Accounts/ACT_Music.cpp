#include "Account_Master.h"
#include "hal/hal.h"

static int onEvent(Account* account, Account::EventParam_t* param)
{
    if (param->event != Account::EVENT_NOTIFY)
    {
        return Account::ERROR_UNSUPPORTED_REQUEST;
    }

    if (param->size != sizeof(AccountSystem::MusicPlayer_Info_t))
    {
        return Account::ERROR_SIZE_MISMATCH;
    }

    AccountSystem::MusicPlayer_Info_t* info = (AccountSystem::MusicPlayer_Info_t*)param->data_p;

    HAL::audio_play_music(info->music);

    return 0;
}

ACCOUNT_INIT_DEF(MusicPlayer)
{
    account->SetEventCallback(onEvent);
}