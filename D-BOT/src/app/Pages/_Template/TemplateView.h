#ifndef __TEMPLATE_VIEW_H
#define __TEMPLATE_VIEW_H

#include "../Page.h"
#define EMOJI_WIDTH (240)
#define EMOJI_HEIGHT (110)
#define EMOJI_SIZE (EMOJI_WIDTH*EMOJI_HEIGHT*3)
#define BIN_HEAD_LENGH   (4)              // bin file has 4 byte head
#define EMOJI_IMG_OFFSET  (240 * 60 * 3)  // row * line

namespace Page
{

class TemplateView
{
public:
    void Create(lv_obj_t* root);
    void update_emoji(unsigned char *buf);
    void Delete();
public:
    struct
    {
        // lv_obj_t* labelTitle;
        // lv_obj_t* labelTick;
        lv_obj_t* canvas;
        lv_group_t* group;
    } ui;

private:

};

}

#endif // !__VIEW_H
