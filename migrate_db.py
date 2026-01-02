#!/usr/bin/env python3
"""
数据库迁移脚本：添加缺失的字段
"""
import sqlite3
import sys

def migrate():
    conn = sqlite3.connect('data/magic.db')
    cursor = conn.cursor()

    # 检查并添加缺失的字段
    migrations = [
        # 商店限购
        ("last_box_buy_date", "DATETIME"),
        ("daily_box_buy_count", "INTEGER DEFAULT 0"),

        # 每日任务系统
        ("daily_tasks", "VARCHAR(100) DEFAULT ''"),
        ("task_progress", "VARCHAR(50) DEFAULT ''"),
        ("task_date", "DATETIME"),

        # 活跃度系统
        ("daily_presence_points", "INTEGER DEFAULT 0"),
        ("total_presence_points", "INTEGER DEFAULT 0"),
        ("last_active_time", "DATETIME"),
        ("presence_levels_claimed", "VARCHAR(50) DEFAULT ''"),

        # 转盘系统
        ("last_wheel_date", "DATETIME"),
        ("wheel_spins_today", "INTEGER DEFAULT 0"),

        # 其他计数器
        ("daily_tarot_count", "INTEGER DEFAULT 0"),
        ("daily_forge_count", "INTEGER DEFAULT 0"),
        ("daily_box_count", "INTEGER DEFAULT 0"),
        ("daily_gift_count", "INTEGER DEFAULT 0"),
    ]

    for column, col_type in migrations:
        # 检查字段是否已存在
        cursor.execute(f"PRAGMA table_info(bindings)")
        columns = [row[1] for row in cursor.fetchall()]

        if column not in columns:
            print(f"添加字段: {column} ({col_type})")
            cursor.execute(f"ALTER TABLE bindings ADD COLUMN {column} {col_type}")
        else:
            print(f"字段已存在: {column}")

    conn.commit()
    conn.close()
    print("\n✅ 数据库迁移完成！")

if __name__ == "__main__":
    migrate()
