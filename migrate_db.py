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
        ("last_box_buy_date", "DATETIME"),
        ("daily_box_buy_count", "INTEGER DEFAULT 0"),
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
