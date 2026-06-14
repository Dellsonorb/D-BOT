#include "hal.h"
#include "config.h"

static bool IsEnable = true;
static int32_t duration = 0;
static uint32_t freq = 0;

static void buzzer_thread(void* argument)
{
    for (;;) {
        if (duration > 0) {
            ledcWriteTone(CONFIG_BUZZ_CHANNEL, freq);
            delay(duration);
            ledcWriteTone(CONFIG_BUZZ_CHANNEL, 0);

            duration = 0;
        }

        delay(50);
    }
}

void HAL::buzz_init(void)
{
    pinMode(CONFIG_BUZZ_PIN, OUTPUT);
    ledcAttachPin(CONFIG_BUZZ_PIN, CONFIG_BUZZ_CHANNEL);
    ledcSetup(CONFIG_BUZZ_CHANNEL, 10000, 8);
    ledcWriteTone(CONFIG_BUZZ_CHANNEL, 0);
    IsEnable = true;
    // Create Buzzer thread
    TaskHandle_t handleBuzzerThread;
    xTaskCreate(
        buzzer_thread,
        "BuzzerThread",
        4096,
        nullptr,
        ESP32_RUNNING_CORE,
        &handleBuzzerThread);
}

void HAL::buzz_set_enable(bool en)
{
    IsEnable = en;
}

void HAL::buzz_tone(uint32_t _freq, int32_t _duration)
{
    if (!IsEnable)
        return;

    if (_duration == 0)
    {
        ledcWriteTone(CONFIG_BUZZ_CHANNEL, _freq);
    } else
    {
        freq = _freq;
        duration = _duration;
    }
}
