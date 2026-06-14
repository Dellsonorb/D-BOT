<h1 align="center">D-BOT: 一个可 AI 控制的无刷平衡车——X-Knob 智能旋钮的变换形态</h1>
<div align="center">

<i>喜欢这个项目吗？请考虑给 Star ⭐️ 以帮助改进！</i>

</div>

D-BOT（Discovery Bot）是一个桌面机器人，可通过 AI 精确控制，同时具备 [X-Knob](https://github.com/SmallPond/X-Knob) 的全功能。D-BOT 支持以下特性：

- [x] [X-Knob](https://github.com/SmallPond/X-Knob) 原生全功能支持;
- [x] 手柄遥控控制（蓝牙）;
- [x] 无线调参：
  - [x] 基于 [SimpleFOCStudio](https://github.com/SmallPond/SimpleFOCStudio) （尝试合入到 upstream 中，但作者太忙一直没时间 review，暂时使用我 fork 的仓库）修改了上位机，通过无线网络连接;
  - [x] 在 D-BOT 端通过 [WirelessTuning](https://github.com/SmallPond/WirelessTuning) 库，作为胶水层无缝适配 SimpleFOC 的 monitor 库；
- [x] 小智 AI 控制，化身 AI 机器人；


![](https://pic-mos-1255408269.cos.ap-guangzhou.myqcloud.com/D-BOT-1.jpg)

### 演示视频

- [【开源】我做了一个不一样的桌面机器人](https://www.bilibili.com/video/BV15FXpYoEGG/)
- [【从开源到共创】"AI 桌面机器人 D-BOT Pro 版" 【附组装教程】](https://www.bilibili.com/video/BV1ioGYziEsY)

D-BOT 交流群：954041464

### 硬件

主要硬件列表：
- 5 块 PCB：主控板 + 驱动板 \* 2 + 屏幕板 + 电池板；
- MCU: ESP32-S3 WROOM-1U-N16R8；
- 屏幕: 240x240 圆形 LCD GC9A01 (1.28 寸)
- 磁编码器：MT6701CT；
- ~~3205a 无刷直流电机（无限位）；~~ 适配了量更多的 3205b 无刷直流电机（无限位）

已经上传到嘉立创开源平台：[硬件开源链接](https://oshwhub.com/dingmos/kbc)

2025-06-21 D-BOT v1.0 版本正式量产了。V1 版本同样开源供大家学习和玩耍。有需要成品的同学可以在淘宝 [45 智造小店](https://item.taobao.com/item.htm?from=cart&id=938721301093&pisk=glTnbKOEQHSQ5jkOXF_I00qgPpiTOw_5ULUReaBrbOW6JXsRehfyedGSOwdPELvOCehC2TKgZI9MEgGCeTWkeQ-K6q3vOB_5zzDxkqee1nVXKJ5P4brNNsGOTHpy2tQ5zxHuXzSIoa9UVwh_4l5NC_fzLaJP7R55aa5FLklGQ_fb4JJyUffNO6PFT9Sz75W1tyyz8g7NQ_1lUWWeUClGZ_QPULSEsClNZkWvzn8ZB2llQKp1nFfhxtRiczzlprIF3nBazxRNtq62TO4zztXmIJOM9v4X6wTpnspK7yvDTnJy0dug-GtesUjXP0UpON6N0TR3Lk5c-9j28MFSMwsyjFbp8YZX6CXFmNKtfvIR-pxfhMosCLAGpL8hbJDOend98GvqBPv5qHJh_ZSyblr4t0U5_bLaVusF11XA7fKpSV19D9Gisod5Y11fHfcgVusF11XxsfqvPM51GtC..&skuId=5834152061817&spm=a1z0d.6639537%2F202410.item.d938721301093.2d457484kVIuBS) 购买。

### 3D 结构

3D 结构的打印件已经上传到 Maker World ： [D-BOT 3D 模型](https://makerworld.com.cn/zh/models/1061527-d-bot-ge-ke-ai-kong-zhi-de-wu-shua-ping-heng-che-x#profileId-1100492)，总共包含 5 个打印件：

- ~~车架-3205a_v1.1~~ 车架 3205b_v0.3
- 车轮适配件_v0.2
- 电池卡扣+底座接口_v0.9
- 屏幕架_v0.4
- 支撑件_v0.1

[硬件 V1 版本对应的结构件](https://makerworld.com.cn/zh/models/1344200-d-botxiang-mu-da-yin-jian-fen-bie-gua-pei-lu-he-ji#profileId-1450090)已更新。

## Getting Started

### 固件下载（推荐）

如果不涉及代码修改，可以直接在 [release 页面](https://github.com/SmallPond/D-BOT/releases)下载最新可用的固件。

### 源码编译

基本环境：
- **VScode + PlatformIO**

1. 下载代码

```
git clone https://github.com/SmallPond/D-BOT  
```

2. pio 编译环境选择

**从 v0.3.1 版本开始， D-BOT 仓库将同时支持硬件 v0.1 和硬件 v1.0 版本，在编译源代码时注意根据自己的硬件版本切换对应的 env。** 图形界面的 env 切换选项在固件烧录的菜单栏附近：“Switch PlatformIO Project Environment”。命令行方式请自行问问 AI。

- HW_V1.0: 最新的量产版本，对应 pio 的 [env:D-BOT-v1_0]
- HW_V0.1: 初代版本，对应 pio 配置的 [env:D-BOT-v0_1]

3. 编译 && flash 

4. 首次启动

- 配置 WiFi，连接 **DBOT_xxx** 的 WiFi，访问 192.168.4.1 进入网页配置并保存，D-BOT 将会自动重启
- 启动后会自动进行陀螺仪（MPU6050）自动校准和电机自动校准（左右电机依次顺逆时针转动）；如果你在完全固定组装前启动过，电机将可能不会再校准导致电机工作不正常；
  - **强制校准方法**：在启动听到“叮”一声后，立马按住 boot 键（ V0.1 主控板最外侧的按键）2 秒不动，等待一会应该能看到电机开始校准；或者**直接 0 地址重刷 merge 固件，这将清除所有配置**。

4. enjoy 

## AI 控制

D-BOT 的 AI 控制代码开源在 [xiaozhi-esp32](https://github.com/SmallPond/xiaozhi-esp32) 仓库。如果你有其他版本的小智，可以在 [xiaozhi-esp32 的 issue 里](https://github.com/SmallPond/xiaozhi-esp32) 提交申请，详细描述板子型号。我统一支持后发 release 固件。当然有能力的同学也可以参考我的修改自行增加其他开发板的支持。

当前已支持的开发板：
- 45coll-sparkbot
- 无名科技1.54寸WIFI版
- Movecall Moji 小智AI衍生版
- 立创·实战派ESP32-S3开发板
- 面包板

MCP 服务器控制实现中...

## 手柄遥控

当前手柄遥控仅支持和我同款的手柄，库开源在[ESP32 解析蓝牙手柄信号](https://github.com/SmallPond/ble_ctrl)。X-Box 理论上可以使用其他库解析。

- 以 L + Home 方式启动手柄；
- 通过小程序“LightBlue 蓝牙工具”扫描出手柄蓝牙，获取蓝牙地址，类似 “04:0A:11:11:90:10”。~~我现在打开这个工具扫描出来的是 UUID 形式的，应该需要改代码，或者通过其他方法获取上述格式的蓝牙地址，有能力的同学可以再研究下。~~ 实际测试使用安卓手机打开小程序可行，ios 打开扫描是 UUID 形式的。
- 刷 D-BOT v0.2 及其以上版本固件，在配网界面填入蓝牙地址；重启后打开手柄就能自动连接；
- D-BOT 默认为 AI 控制模式，按下 A 键切换为遥控模式后，即可通过摇杆控制。

## 无线调参

1. 配置 [SimpleFOCStudio](https://github.com/SmallPond/SimpleFOCStudio)基本环境 ；
2. 通过串口获取 D-BOT 启动日志打印的 IP 地址；
3. 在 SimpleFOCStudio 界面中配置 IP 和端口号（默认为 4242），连接成功后，在 Command Line interface 处输入以下指令调参；

| 对象 | 命令 | 示例 |
| :-----| ----: | :----: |
| 直立环 | S | SP0.2——直立环 P 项设置为 0.2， SP不带参数则为获取当前 P 项 |
| 速度环 | V | VP0.2——速度环 P 项设置为 0.2 |
| 转向环 | T | TP0.2——转向环 P 项设置为 0.2 |
| D-BOT 前后移动闭环控制 | R | RP0.2|
| D-BOT 转向闭环控制 | B | BP0.2|
| 机械中值 | X | X-3——机械中值设置为 -3（默认值为 -2，正常直立时 D-BOT 向前走，应该减小该值） |
|保存所有参数|C|C|

## 致谢开源

- [Super_Balance](https://gitee.com/handmade-rice/Super_Balance): 手工饭开源平衡车；本项目的结构和小车平衡控制主要参考此项目

### 相关项目

- [sparkbot-45coll](https://gitee.com/coll45/sparkbot-45coll)
- [SimpleFOCStudio](https://github.com/JorgeMaker/SimpleFOCStudio)
- [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=SmallPond/D-BOT&type=Date)](https://www.star-history.com/#SmallPond/D-BOT&Date)

