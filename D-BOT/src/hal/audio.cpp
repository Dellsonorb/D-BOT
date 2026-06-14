#include "hal.h"
#include "app/Utils/TonePlayer/TonePlayer.h"
#include "lvgl.h"
#include "app/Utils/TonePlayer/MusicCode.h"

static TonePlayer player;

static void tone_callback(uint32_t freq, uint16_t volume)
{
    HAL::buzz_tone(freq);
}

void HAL::audio_init(void)
{
    player.SetCallback(tone_callback);
}

void HAL::audio_update(void)
{
    player.Update(lv_tick_get());
}

bool HAL::audio_play_music(const char* name)
{
    bool retval = false;
    for (int i = 0; i < sizeof(MusicList) / sizeof(MusicList[0]); i++)
    {
        if (strcmp(name, MusicList[i].name) == 0)
        {
            player.Play(MusicList[i].mc, MusicList[i].length);
            retval = true;
            break;
        }
    }
    return retval;
}
