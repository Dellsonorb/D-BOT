#!/bin/bash

# ==========================================
# 项目名称：小智 AI Linux 客户端启动脚本 (完全体)
# 适用环境：Ubuntu 24.04 + Conda + Fcitx5
# ==========================================

# --- 1. 核心路径配置 ---
PROJECT_DIR="/home/doer/Project/py-xiaozhi-main"
# 使用 Conda 环境下的 Python 绝对路径，确保脱离终端也能运行
PYTHON_EXE="/home/doer/miniconda3/envs/py-xiaozhi/bin/python"
# 指向我们手动建立软链接的插件目录
CONDA_QT_PLUGINS="/home/doer/miniconda3/envs/py-xiaozhi/plugins"

# 切换工作目录
cd "$PROJECT_DIR" || exit

echo "------------------------------------------------"
echo "🚀 小智 AI (py-xiaozhi) 正在以【完全体模式】启动..."
echo "------------------------------------------------"

# --- 2. 环境清理 (防崩溃) ---
# 必须取消 LD_PRELOAD，否则可能导致 Qt 界面库冲突并引发“段错误”
unset LD_PRELOAD

# --- 3. 输入法兼容性配置 (Fcitx5) ---
# 这一块确保你的中文输入法在任何启动方式下都生效
export QT_IM_MODULE=fcitx
export XMODIFIERS="@im=fcitx"
export GTK_IM_MODULE=fcitx
export SDL_IM_MODULE=fcitx
# 强制 Qt 搜索我们手动链接了 libfcitx5 插件的目录
export QT_PLUGIN_PATH="$CONDA_QT_PLUGINS"

# --- 4. 音频系统路径 (PipeWire/ALSA 桥接) ---
# 确保程序能正确识别麦克风并走系统默认音频流，解决 -9985 等设备占用报错
export ALSA_CONFIG_PATH=/usr/share/alsa/alsa.conf
export ALSA_PLUGIN_DIRS=/usr/lib/x86_64-linux-gnu/alsa-lib

# --- 5. 启动程序 ---
echo "📂 项目目录: $PROJECT_DIR"
echo "🐍 执行环境: $PYTHON_EXE"
echo "✨ 输入法状态: Fcitx 桥接已就绪"
echo "------------------------------------------------"

# 运行主程序
"$PYTHON_EXE" main.py

# --- 6. 异常捕获与保活 ---
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ 程序运行出错退出 (退出代码: $EXIT_CODE)"
    echo "提示：如果麦克风无法工作，请确认没有其他程序独占声卡。"
    read -p "按回车键关闭窗口..."
else
    echo "👋 小智已安全退出。"
fi
