"""
数据库迁移：给api_keys表增加限额字段
运行方式：python migrate_add_api_key_limits.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'chemlearn.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查现有列
    cursor.execute("PRAGMA table_info(api_keys)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"现有列: {columns}")

    # 增加新列
    new_columns = [
        ('daily_limit', 'INTEGER DEFAULT 1000'),
        ('rate_limit_per_minute', 'INTEGER DEFAULT 60'),
        ('daily_call_count', 'INTEGER DEFAULT 0'),
        ('last_call_date', 'VARCHAR(10)'),
    ]

    for col_name, col_def in new_columns:
        if col_name not in columns:
            print(f"增加列: {col_name}")
            cursor.execute(f"ALTER TABLE api_keys ADD COLUMN {col_name} {col_def}")
        else:
            print(f"列已存在: {col_name}")

    conn.commit()
    conn.close()
    print("迁移完成！")

if __name__ == '__main__':
    migrate()
