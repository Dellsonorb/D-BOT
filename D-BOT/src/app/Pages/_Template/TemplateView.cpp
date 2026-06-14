#include "TemplateView.h"
#include <stdio.h>
#include "lvgl.h"

using namespace Page;

const char *emoji_path = "S:/emoji/";

void TemplateView::Create(lv_obj_t* root)
{
	lv_obj_remove_style_all(root);
	lv_obj_set_size(root, LV_HOR_RES, LV_VER_RES);
	lv_obj_set_style_bg_color(root, lv_color_black(), 0);

	// lv_obj_t* label = lv_label_create(root);
	// lv_obj_set_style_text_font(label, &lv_font_montserrat_14, 0);
	// lv_obj_set_style_text_color(label, lv_color_white(), 0);
	// lv_obj_align(label, LV_ALIGN_TOP_MID, 0, 30);
	// lv_label_set_text(label, "");
	// ui.labelTitle = label;

	lv_obj_t* img = lv_img_create(root);
	lv_img_set_src(img, Resource.GetImage("emoji"));
	// lv_img_set_src(img, "S:/emoji/wink/wink0001.bin");
	lv_obj_center(img);
	ui.canvas = img;

	// label = lv_label_create(root);
	// lv_obj_set_style_text_font(label, &lv_font_montserrat_10, 0);
	// lv_obj_set_style_text_color(label, lv_color_make(0,0,0), 0);
	// lv_label_set_text(label, "label tick");
	// lv_obj_align(label, LV_ALIGN_TOP_MID, 50, 50);
	// ui.labelTick = label;

	ui.group = lv_group_create();
	lv_indev_set_group(lv_get_indev(LV_INDEV_TYPE_ENCODER), ui.group);

	lv_group_add_obj(ui.group, ui.canvas);
	// lv_group_add_obj(ui.group, ui.labelTitle);
	// lv_group_focus_obj(ui.canvas);
	lv_group_focus_obj(ui.canvas);

}

lv_img_dsc_t img_emoji = {
	{
		LV_IMG_CF_TRUE_COLOR_ALPHA, 
		0,
		0,
		EMOJI_WIDTH,
		EMOJI_HEIGHT,
	},
	EMOJI_SIZE,
	NULL
};


const char *g_emoji_name[] = {
	"wink",
	// "angry_in",
	// "angry_loop",
	// "angry_out",
	"max"
};

void TemplateView::update_emoji(unsigned char *buf)
{
	lv_fs_file_t lv_emoji;
	lv_fs_res_t  lv_res;
	static int pcnt=1;
	char filename[128];
	static unsigned long next_display_time = 0;
	uint32_t read_num;
	static uint32_t emoji_index = 0;

	if (lv_tick_get() < next_display_time) {
		return;
	}

	if (strcmp(g_emoji_name[emoji_index], "max") == 0) {
		emoji_index = 0;
		next_display_time = lv_tick_get() + 1500;
		return;

	}
	const char *emoji_name = g_emoji_name[emoji_index];
	// path: S:/emoji/angry_in/angry_in0001.bin
	snprintf(filename, sizeof(filename), "%s%s/%s%04d.bin", 
				emoji_path, emoji_name, emoji_name, pcnt);
	// LV_LOG_INFO("open file %s", filename);
	lv_res = lv_fs_open(&lv_emoji, filename , LV_FS_MODE_RD);
	if(lv_res != LV_FS_RES_OK) {
		// LV_LOG_ERROR("open file %s failed", filename);
		pcnt = 1;
		emoji_index++;
		return;
	}
	lv_fs_seek(&lv_emoji, BIN_HEAD_LENGH + EMOJI_IMG_OFFSET, LV_FS_SEEK_SET);
	lv_res = lv_fs_read(&lv_emoji, buf, EMOJI_SIZE, &read_num);
	if(lv_res != LV_FS_RES_OK || read_num != EMOJI_SIZE) {
		LV_LOG_ERROR("read file size %d, read out %d.", EMOJI_SIZE, read_num);
	}

	lv_fs_close(&lv_emoji);

	img_emoji.data = buf;
	lv_img_set_src(ui.canvas, &img_emoji);
	pcnt++;
}


void TemplateView::Delete()
{
	lv_group_del(ui.group);
}
