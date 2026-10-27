"""
高考化学真题统一导入脚本（2026-10 合并版）

替代原来 15 份复制粘贴的 import_gaokao_*.py / import_2024_*.py 脚本。
题目数据已提取为 import_data/*.json（共 15 个批次 / 435 道题），
原脚本的完整内容保留在 git 历史（基线提交 cb4fbe3）中。

用法：
    python import_gaokao_unified.py                # 导入全部批次
    python import_gaokao_unified.py batch2 batch9  # 只导入指定批次（文件名去掉 import_ 前缀和 .json）
    python import_gaokao_unified.py --list         # 查看可用批次与题量

数据库路径：
    默认 ~/chemlearn/backend/chemlearn.db（与原脚本一致）
    可用环境变量 CHEMLEARN_DB 覆盖。
"""
import json
import os
import sqlite3
import sys

BACKEND = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND, "import_data")

COLUMNS = ("question_code", "title", "content", "question_type", "difficulty",
           "grade", "knowledge_point", "options", "answer", "analysis",
           "source", "images", "keywords", "sub_questions")

INSERT_SQL = (
    "INSERT INTO questions (" + ",".join(COLUMNS) + ",creator_id) "
    "VALUES (" + ",".join("?" * (len(COLUMNS) + 1)) + ")"
)


def db_path():
    return os.environ.get(
        "CHEMLEARN_DB",
        os.path.expanduser("~/chemlearn/backend/chemlearn.db"),
    )


def list_batches():
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".json"))
    for f in files:
        data = json.load(open(os.path.join(DATA_DIR, f), encoding="utf-8"))
        name = f[len("import_"):-len(".json")]
        print(f"  {name:<22} {len(data):>4} 题")
    print(f"  {'合计':<22} {sum(len(json.load(open(os.path.join(DATA_DIR, f), encoding='utf-8'))) for f in files):>4} 题")


def import_batches(batch_names):
    path = db_path()
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # 与原省卷脚本一致：归属到 admin 名下
    row = cursor.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    creator_id = row[0] if row else 1

    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".json"))
    if batch_names:
        files = [
            f for f in files
            if f[len("import_"):-len(".json")] in batch_names
        ]
        missing = set(batch_names) - {f[len("import_"):-len(".json")] for f in files}
        if missing:
            print(f"未找到批次: {', '.join(sorted(missing))}")
            conn.close()
            sys.exit(1)

    inserted = skipped = 0
    for f in files:
        data = json.load(open(os.path.join(DATA_DIR, f), encoding="utf-8"))
        batch_inserted = batch_skipped = 0
        for q in data:
            code = q.get("question_code")
            if not code:
                print(f"  !! 跳过缺 question_code 的记录: {q.get('title', '?')[:30]}")
                batch_skipped += 1
                continue
            if cursor.execute("SELECT id FROM questions WHERE question_code=?", (code,)).fetchone():
                batch_skipped += 1
                continue
            values = [
                q.get(col) if q.get(col) not in ("",) else None
                for col in COLUMNS
            ]
            # options/sub_questions 若是 list/dict 则序列化（原省卷脚本在数据里已 dumps，兼容两种形态）
            for i, col in enumerate(COLUMNS):
                if col in ("options", "sub_questions", "keywords", "images") and isinstance(values[i], (list, dict)):
                    values[i] = json.dumps(values[i], ensure_ascii=False)
            cursor.execute(INSERT_SQL, values + [creator_id])
            batch_inserted += 1
        conn.commit()
        name = f[len("import_"):-len(".json")]
        print(f"  {name:<22} 新增 {batch_inserted:>3}  跳过(已存在) {batch_skipped:>3}")
        inserted += batch_inserted
        skipped += batch_skipped

    conn.close()
    print(f"\n导入完成！新增 {inserted} 道，跳过 {skipped} 道 -> {path}")


def main():
    args = sys.argv[1:]
    if "--list" in args:
        list_batches()
    else:
        batches = [a for a in args if not a.startswith("-")]
        import_batches(batches)


if __name__ == "__main__":
    main()
