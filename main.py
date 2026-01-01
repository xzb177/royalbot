import logging
import os
import sys
import importlib
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 确保能导入根目录模块
sys.path.insert(0, str(Path(__file__).parent))

from config import Config

# 加载配置
Config.validate()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_plugins(app):
    plugin_dir = "plugins"
    if not os.path.exists(plugin_dir):
        print(f"❌ 插件目录不存在: {plugin_dir}")
        return

    # 动态加载所有 .py 文件
    for filename in os.listdir(plugin_dir):
        if filename.endswith(".py"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"plugins.{module_name}")
                if hasattr(module, "register"):
                    module.register(app)
                    print(f"✨ 魔法模块已装载: {module_name}")
            except Exception as e:
                print(f"💥 模块加载失败 {module_name}: {e}")

if __name__ == '__main__':
    print("🪄 正在唤醒云海看板娘...")
    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    load_plugins(app)

    print("✅ 魔法阵启动成功！Bot is running...")
    app.run_polling()
