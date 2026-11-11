#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 Windows 本地部署器的运行时包 payload_chem.tar.gz。

组装顺序（全部来自当前仓库，无需外部 assets）：
    backend/app/**           后端源码
    backend/chemlearn.db     清洗过的题库数据库（只留题库 + 内置管理员）
    web/dist/app/**          前端构建产物（npm run build 的产物）
    deploy/requirements.txt  依赖清单，便于排障 / Linux 端复用
    payload.json             构建信息（版本、题量、文件数）

为什么要清洗数据库：仓库里的 chemlearn.db 是开发库，带有 13 个测试账号、
练习记录和 API Key。直接分发会把别人的账号和密码哈希一起发出去，因此这里
只保留题库与 admin，其余业务表清空。

用法：
    python build_payload.py
    python build_payload.py --keep-users      # 保留开发库账号（仅本地调试）
    python build_payload.py --source-db D:/other.db
"""
import argparse
import datetime
import json
import os
import shutil
import sqlite3
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

BACKEND = os.path.join(REPO, "backend")
WEB_DIST = os.path.join(REPO, "web", "dist", "app")
DEFAULT_DB = os.path.join(BACKEND, "chemlearn.db")
DEFAULT_OUT = os.path.join(HERE, "payload_chem.tar.gz")
STAGE = os.path.join(HERE, "build", "payload")

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git",
                                "node_modules", ".venv", ".DS_Store")

# 这些表承载题库本身，清洗时保留
KEEP_TABLES = {"questions", "users"}


def read_version():
    """版本号单一来源：win_deployer.py 里的 VERSION"""
    path = os.path.join(HERE, "win_deployer.py")
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "0.0.0"


def sanitize_db(src, dst, keep_users=False):
    """复制一份数据库并清除开发期数据，返回统计信息。"""
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copy2(src, dst)

    con = sqlite3.connect(dst)
    try:
        tables = [r[0] for r in con.execute(
            "select name from sqlite_master where type='table' "
            "and name not like 'sqlite_%'")]
        before = {t: con.execute("select count(*) from '%s'" % t).fetchone()[0]
                  for t in tables}

        admin = con.execute(
            "select id, username from users where role = 'ADMIN' "
            "order by id limit 1").fetchone()
        if not admin:
            raise SystemExit("源数据库里没有 ADMIN 账号，无法生成部署库")

        if not keep_users:
            con.execute("delete from users where id <> ?", (admin[0],))
            for table in tables:
                if table not in KEEP_TABLES:
                    con.execute("delete from '%s'" % table)
            # 题目创建者统一指回内置管理员，避免悬空外键
            con.execute("update questions set creator_id = ?", (admin[0],))
            # 有 AUTOINCREMENT 才有 sqlite_sequence，重置它让新库 id 从 1 开始
            has_seq = con.execute(
                "select 1 from sqlite_master where type='table' "
                "and name='sqlite_sequence'").fetchone()
            if has_seq:
                con.execute(
                    "delete from sqlite_sequence where name in (%s)"
                    % ",".join("?" * len(tables)), tables)

        con.commit()
        con.execute("vacuum")

        after = {t: con.execute("select count(*) from '%s'" % t).fetchone()[0]
                 for t in tables}
        stats = {
            "users_before": before.get("users", 0),
            "users_after": after.get("users", 0),
            "questions": after.get("questions", 0),
            "rows_removed": sum(before.values()) - sum(after.values()),
            "admin": admin[1],
        }

        # 题目里引用的图片文件是否缺失（仓库 uploads 目录可能为空）
        with_img = con.execute(
            "select count(*) from questions where images is not null "
            "and images not in ('', '[]', 'null')").fetchone()[0]
        stats["questions_with_images"] = with_img
        return stats
    finally:
        con.close()


def check_prereq():
    missing = []
    if not os.path.isdir(os.path.join(BACKEND, "app")):
        missing.append("backend/app（后端源码）")
    if not os.path.isfile(DEFAULT_DB):
        missing.append("backend/chemlearn.db（题库数据库）")
    if not os.path.isfile(os.path.join(WEB_DIST, "index.html")):
        missing.append("web/dist/app（先在 web/ 执行 npm run build）")
    if missing:
        print("缺少以下文件，无法打包：")
        for item in missing:
            print("  - " + item)
        sys.exit(2)


def build_stage(source_db, keep_users):
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)

    # 1) 后端源码
    shutil.copytree(os.path.join(BACKEND, "app"),
                    os.path.join(STAGE, "backend", "app"), ignore=IGNORE)

    # 2) 数据库（清洗）
    db_dst = os.path.join(STAGE, "backend", "chemlearn.db")
    stats = sanitize_db(source_db, db_dst, keep_users=keep_users)

    # 3) 前端产物
    shutil.copytree(WEB_DIST, os.path.join(STAGE, "web", "dist", "app"),
                    ignore=IGNORE)

    # 4) 依赖清单：目标机不需要 pip，但出问题时能直接对照排查
    deploy_dir = os.path.join(STAGE, "deploy")
    os.makedirs(deploy_dir)
    shutil.copy2(os.path.join(BACKEND, "requirements.txt"),
                 os.path.join(deploy_dir, "requirements.txt"))

    version = read_version()
    files = sum(len(names) for _, _, names in os.walk(STAGE))
    meta = {
        "name": "chemlearn-windows-payload",
        "version": version,
        "built_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_db": os.path.abspath(source_db),
        "users": stats["users_after"],
        "questions": stats["questions"],
        "rows_removed": stats["rows_removed"],
        "files": files,
    }
    with open(os.path.join(STAGE, "payload.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(STAGE, "VERSION"), "w", encoding="utf-8") as f:
        f.write(version + "\n")
    return stats, meta


def pack(out_path):
    if os.path.exists(out_path):
        os.remove(out_path)
    with tarfile.open(out_path, "w:gz") as tar:
        for name in sorted(os.listdir(STAGE)):
            tar.add(os.path.join(STAGE, name), arcname=name)
    return os.path.getsize(out_path)


def main():
    parser = argparse.ArgumentParser(description="构建 Windows 部署器运行时包")
    parser.add_argument("--source-db", default=DEFAULT_DB)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--keep-users", action="store_true",
                        help="保留开发库账号（默认只留 admin）")
    parser.add_argument("--keep-stage", action="store_true",
                        help="打包后保留 build/payload 便于检查")
    args = parser.parse_args()

    check_prereq()
    stats, meta = build_stage(args.source_db, args.keep_users)
    size = pack(args.out)

    print("运行时包已生成：%s" % args.out)
    print("  版本      %s" % meta["version"])
    print("  体积      %.2f MB" % (size / 1048576.0))
    print("  文件数    %d" % meta["files"])
    print("  题库      %d 题（其中 %d 题带图片字段）"
          % (stats["questions"], stats["questions_with_images"]))
    print("  账号      %d -> %d（%s）"
          % (stats["users_before"], stats["users_after"], stats["admin"]))
    print("  清理行数  %d" % stats["rows_removed"])
    if stats["questions_with_images"]:
        print("  注意：题库引用了图片，但上传目录不随包分发，"
              "这些题的图片会显示不出来（不影响做题）")

    if not args.keep_stage:
        shutil.rmtree(STAGE, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
