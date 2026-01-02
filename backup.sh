#!/bin/bash
#
# RoyalBot 自动备份脚本
# 每天备份数据库并通过 Telegram Bot 发送
#

set -e

# 配置
BOT_DIR="/root/royalbot"
DATA_DIR="$BOT_DIR/data"
DB_FILE="$DATA_DIR/magic.db"
BACKUP_DIR="$DATA_DIR/backups"
OWNER_ID=$(grep "OWNER_ID" "$BOT_DIR/.env" 2>/dev/null | cut -d'=' -f2)
BOT_TOKEN=$(grep "BOT_TOKEN" "$BOT_DIR/.env" 2>/dev/null | cut -d'=' -f2)
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/magic_$DATE.db"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 检查数据库文件
if [ ! -f "$DB_FILE" ]; then
    echo "错误: 数据库文件不存在 $DB_FILE"
    exit 1
fi

# 复制数据库
cp "$DB_FILE" "$BACKUP_FILE"

# 压缩备份
gzip "$BACKUP_FILE"
BACKUP_FILE="$BACKUP_FILE.gz"

# 获取文件大小
FILE_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)

# 检查文件大小（Telegram Bot 限制 50MB）
if [ "$FILE_SIZE" -gt 52428800 ]; then
    echo "警告: 备份文件超过 50MB，无法通过 Bot 发送"
    echo "备份文件: $BACKUP_FILE"
    exit 1
fi

# 通过 Telegram Bot 发送备份
if [ -n "$BOT_TOKEN" ] && [ -n "$OWNER_ID" ]; then
    RESPONSE=$(curl -s -X POST \
        "https://api.telegram.org/bot$BOT_TOKEN/sendDocument" \
        -F "chat_id=$OWNER_ID" \
        -F "document=@$BACKUP_FILE" \
        -F "caption=📦 RoyalBot 数据库备份\n📅 $(date '+%Y-%m-%d %H:%M:%S')\n💾 文件大小: $((FILE_SIZE / 1024)) KB\n━━━━━━━━━━━━━━━━━━\n<i>自动备份，请妥善保存~ (｡•̀ᴗ-)✧</i>" \
        -F "parse_mode=HTML")

    # 检查发送结果
    if echo "$RESPONSE" | grep -q '"ok":true'; then
        echo "✅ 备份已发送到 Telegram"
    else
        echo "❌ 发送失败: $RESPONSE"
        exit 1
    fi
else
    echo "错误: BOT_TOKEN 或 OWNER_ID 未配置"
    exit 1
fi

# 清理 7 天前的旧备份
find "$BACKUP_DIR" -name "magic_*.db.gz" -mtime +7 -delete 2>/dev/null || true

# 保留本地最新备份（不超过 5 个）
ls -t "$BACKUP_DIR"/magic_*.db.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

echo "备份完成: $BACKUP_FILE"
