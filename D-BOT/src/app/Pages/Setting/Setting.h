#ifndef __SETTING_H__
#define __SETTING_H__


#include "SettingModel.h"
#include "SettingView.h"
#include "config.h"


namespace Page
{
    class Setting : public PageBase
    {
    public:
        Setting();
        virtual ~Setting();

        virtual void onCustomAttrConfig();
        virtual void onViewLoad();
        virtual void onViewDidLoad();
        virtual void onViewWillAppear();
        virtual void onViewDidAppear();
        virtual void onViewWillDisappear();
        virtual void onViewDidDisappear();
        virtual void onViewDidUnload();

        void SettingEventHandler(lv_event_t* event, lv_event_code_t code);

    private:
        void Update();
        void AttachEvent(lv_obj_t* obj);
        static void onTimerUpdate(lv_timer_t* timer);
        static void onEvent(lv_event_t* event);
        
    private:
        SettingView* View;
        SettingModel* Model;
        lv_timer_t* timer;
    };
}


#endif /*   __Setting_H__ */