#!/usr/bin/env python3
"""
发送更新通知到群组
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram import Bot
from config import Config

async def send_update():
    """发送更新通知"""
    bot = Bot(token=Config.BOT_TOKEN)

    message = """
📢 【 系 统 更 新 通 知 】
━━━━━━━━━━━━━━━━━━

✨ RoyalBot 代码质量保障体系完成！

🔧 主要更新：

1️⃣ 代码质量保障
   • 修复 17 个插件的数据库会话管理问题
   • 新增代码检查脚本（7种错误模式检测）
   • 新增 9 个代码模式测试用例
   • 总测试数：28 个全部通过 ✅

2️⃣ CI/CD 自动化
   • 配置 GitHub Actions 自动测试
   • PR 模板和贡献指南
   • pre-commit hook 自动检查

3️⃣ 新功能
   • Emby 媒体库监控推送
   • 有奖推送系统
   • 幸运转盘
   • 每日任务系统

📊 测试结果：28 passed

📖 文档更新：ai.md + CODE_QUALITY.md

"代码质量，从今开始！(｡•̀ᴗ-)✧"
━━━━━━━━━━━━━━━━━━
"""

    if Config.GROUP_ID:
        await bot.send_message(chat_id=Config.GROUP_ID, text=message)
        print("✅ 更新通知已发送到群组")
    else:
        print("⚠️ 未配置 GROUP_ID，跳过群组通知")

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_update())
