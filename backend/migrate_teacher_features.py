"""
数据库迁移：添加班级、作业、考试相关表和字段
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "chemlearn.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 给users表加class_id字段
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN class_id INTEGER")
        print("✓ users.class_id 字段已添加")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("○ users.class_id 已存在")
        else:
            raise

    # 2. 创建班级表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(64) NOT NULL,
            grade VARCHAR(32),
            description VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ classes 表已创建")

    # 3. 创建老师-班级关联表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    print("✓ teacher_classes 表已创建")

    # 4. 创建作业表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(128) NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            question_ids JSON DEFAULT '[]',
            start_time DATETIME,
            end_time DATETIME,
            status VARCHAR(20) DEFAULT 'draft',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        )
    """)
    print("✓ assignments 表已创建")

    # 5. 创建作业-班级关联表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    print("✓ assignment_classes 表已创建")

    # 6. 创建作业提交表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            answers JSON DEFAULT '{}',
            score INTEGER,
            total_score INTEGER DEFAULT 0,
            submitted_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    """)
    print("✓ assignment_submissions 表已创建")

    # 7. 创建考试表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(128) NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            duration INTEGER DEFAULT 60,
            total_score INTEGER DEFAULT 100,
            start_time DATETIME,
            end_time DATETIME,
            status VARCHAR(20) DEFAULT 'draft',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        )
    """)
    print("✓ exams 表已创建")

    # 8. 创建考试-班级关联表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    print("✓ exam_classes 表已创建")

    # 9. 创建考试题目表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            "order" INTEGER DEFAULT 0,
            score INTEGER DEFAULT 5,
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)
    print("✓ exam_questions 表已创建")

    # 10. 创建考试提交表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            answers JSON DEFAULT '{}',
            score INTEGER,
            started_at DATETIME,
            submitted_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    """)
    print("✓ exam_submissions 表已创建")

    # 11. 插入示例班级
    cursor.execute("SELECT COUNT(*) FROM classes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO classes (name, grade, description) VALUES (?, ?, ?)",
            [
                ("高一1班", "高一", "示例班级"),
                ("高一2班", "高一", "示例班级"),
                ("高二1班", "高二", "示例班级"),
            ]
        )
        print("✓ 示例班级已插入")

    conn.commit()
    conn.close()
    print("\n✅ 数据库迁移完成！")


if __name__ == "__main__":
    migrate()
