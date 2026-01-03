#!/usr/bin/env python3
"""
为现有数据库添加 Emby 观影相关字段
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

def add_emby_fields():
    """添加 Emby 观影字段到现有数据库"""
    pg_url = os.getenv("DB_URL", "postgresql://royalbot:RoyalBot_2026_Secure_Key_8847@postgres:5432/royalbot")
    engine = create_engine(pg_url, echo=False)
    
    with engine.connect() as conn:
        # 检查现有字段
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'bindings' AND column_name IN (
                'daily_watch_minutes', 'total_watch_minutes', 
                'last_watch_claimed', 'early_bird_wins'
            )
        """)).fetchall()
        
        existing = {row[0] for row in result}
        print(f"现有字段: {existing}")
        
        fields_to_add = {
            'daily_watch_minutes': 'INTEGER DEFAULT 0',
            'total_watch_minutes': 'INTEGER DEFAULT 0', 
            'last_watch_claimed': 'TIMESTAMP',
            'early_bird_wins': 'INTEGER DEFAULT 0'
        }
        
        for field, field_type in fields_to_add.items():
            if field not in existing:
                sql = f"ALTER TABLE bindings ADD COLUMN {field} {field_type}"
                print(f"执行: {sql}")
                conn.execute(text(sql))
                print(f"✅ 添加字段: {field}")
            else:
                print(f"⚠️ 字段已存在: {field}")
        
        conn.commit()
        print("\n✅ Emby 字段迁移完成！")

if __name__ == "__main__":
    add_emby_fields()
