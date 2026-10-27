"""
完整数据库迁移：检查并补齐api_keys表所有缺失字段
运行方式：python migrate_api_keys_full.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'chemlearn.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'")
    if not cursor.fetchone():
        print("api_keys表不存在，创建表...")
        cursor.execute("""
            CREATE TABLE api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(128) NOT NULL,
                key VARCHAR(128) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                scope VARCHAR(256) DEFAULT 'all',
                is_active BOOLEAN DEFAULT 1,
                call_count INTEGER DEFAULT 0,
                daily_limit INTEGER DEFAULT 1000,
                rate_limit_per_minute INTEGER DEFAULT 60,
                daily_call_count INTEGER DEFAULT 0,
                last_call_date VARCHAR(10),
                created_at DATETIME,
                expires_at DATETIME
            )
        """)
        conn.commit()
        print("表创建完成！")
        conn.close()
        return

    # 检查现有列
    cursor.execute("PRAGMA table_info(api_keys)")
    columns = {row[1]: row for row in cursor.fetchall()}
    print(f"现有列: {list(columns.keys())}")

    # 需要的所有列及定义
    required_columns = [
        ('name', 'VARCHAR(128) NOT NULL'),
        ('key', 'VARCHAR(128) UNIQUE NOT NULL'),
        ('user_id', 'INTEGER NOT NULL'),
        ('scope', 'VARCHAR(256) DEFAULT "all"'),
        ('is_active', 'BOOLEAN DEFAULT 1'),
        ('call_count', 'INTEGER DEFAULT 0'),
        ('daily_limit', 'INTEGER DEFAULT 1000'),
        ('rate_limit_per_minute', 'INTEGER DEFAULT 60'),
        ('daily_call_count', 'INTEGER DEFAULT 0'),
        ('last_call_date', 'VARCHAR(10)'),
        ('created_at', 'DATETIME'),
        ('expires_at', 'DATETIME'),
    ]

    for col_name, col_def in required_columns:
        if col_name not in columns:
            print(f"增加缺失列: {col_name}")
            try:
                cursor.execute(f"ALTER TABLE api_keys ADD COLUMN {col_name} {col_def}")
            except Exception as e:
                print(f"  增加 {col_name} 失败: {e}")
        else:
            print(f"列已存在: {col_name}")

    conn.commit()

    # 验证
    cursor.execute("PRAGMA table_info(api_keys)")
    final_columns = [row[1] for row in cursor.fetchall()]
    print(f"\n最终列: {final_columns}")

    # 给现有数据设置默认值
    cursor.execute("UPDATE api_keys SET scope='all' WHERE scope IS NULL OR scope=''")
    cursor.execute("UPDATE api_keys SET is_active=1 WHERE is_active IS NULL")
    cursor.execute("UPDATE api_keys SET call_count=0 WHERE call_count IS NULL")
    cursor.execute("UPDATE api_keys SET daily_limit=1000 WHERE daily_limit IS NULL")
    cursor.execute("UPDATE api_keys SET rate_limit_per_minute=60 WHERE rate_limit_per_minute IS NULL")
    cursor.execute("UPDATE api_keys SET daily_call_count=0 WHERE daily_call_count IS NULL")
    conn.commit()

    # 统计
    cursor.execute("SELECT COUNT(*) FROM api_keys")
    count = cursor.fetchone()[0]
    print(f"\n现有API Key数量: {count}")

    conn.close()
    print("\n迁移完成！")

if __name__ == '__main__':
    migrate()
