# -*- coding: utf-8 -*-
"""组装一键部署工具的内嵌部署包 payload.tar.gz

结构:
  {学科}/backend/app/...          后端源码
  {学科}/backend/{db}.db          干净数据库(已从服务器 VACUUM 导出)
  {学科}/web/dist/app/...         前端构建产物
  portal/index.html, api-platform.html
  deploy/requirements.txt         Python 依赖锁定(与线上一致)
"""
import os
import shutil
import tarfile

BASE = r"D:/学习中心/部署工具"
SRC_BASE = r"D:/学习中心"
ASSETS = os.path.join(BASE, "assets")
PAYLOAD_DIR = os.path.join(BASE, "payload")
OUT = os.path.join(BASE, "payload.tar.gz")

SUBJECTS = [("chem", "化学"), ("math", "数学"), ("phys", "物理"),
            ("bio", "生物"), ("chn", "语文"), ("eng", "英语")]
DBS = {"chem": "chemlearn.db", "math": "mathlearn.db", "phys": "physicslearn.db",
       "bio": "biolearn.db", "chn": "chineselearn.db", "eng": "englishlearn.db"}

REQUIREMENTS = """\
aiosqlite==0.22.1
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
bcrypt==4.0.1
certifi==2026.7.22
click==8.5.0
et_xmlfile==2.0.0
fastapi==0.143.0
greenlet==3.5.6
h11==0.16.0
httpcore==1.0.9
httptools==0.9.0
httpx==0.28.1
idna==3.20
openpyxl==3.1.5
opentelemetry-api==1.45.1
passlib==1.7.4
psutil==7.2.2
pydantic==2.14.1
pydantic-settings==2.15.0
pydantic_core==2.50.1
PyJWT==2.15.1
pypinyin==0.55.0
python-dotenv==1.2.4
python-multipart==0.0.32
PyYAML==6.0.3
SQLAlchemy==2.1.4
starlette==1.7.0
typing-inspection==0.4.4
typing_extensions==4.16.0
uvicorn==0.54.0
uvloop==0.23.0
watchfiles==1.3.0
websockets==17.2
"""

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "node_modules", ".venv")


def main():
    if os.path.exists(PAYLOAD_DIR):
        shutil.rmtree(PAYLOAD_DIR)
    os.makedirs(PAYLOAD_DIR)

    total = 0
    for key, sub in SUBJECTS:
        src_root = os.path.join(SRC_BASE, sub, "01-源代码")
        # 后端源码
        shutil.copytree(os.path.join(src_root, "backend", "app"),
                        os.path.join(PAYLOAD_DIR, sub, "backend", "app"), ignore=IGNORE)
        # 数据库（服务器导出的干净副本）
        shutil.copy2(os.path.join(ASSETS, "dbs", DBS[key]),
                     os.path.join(PAYLOAD_DIR, sub, "backend", DBS[key]))
        # 前端构建产物
        shutil.copytree(os.path.join(src_root, "web", "dist", "app"),
                        os.path.join(PAYLOAD_DIR, sub, "web", "dist", "app"), ignore=IGNORE)
        print(f"[ok] {sub}: app + {DBS[key]} + dist")

    # 门户
    portal_dir = os.path.join(PAYLOAD_DIR, "portal")
    os.makedirs(portal_dir)
    shutil.copy2(os.path.join(ASSETS, "portal", "index.html"), portal_dir)
    shutil.copy2(os.path.join(ASSETS, "portal", "api-platform.html"), portal_dir)
    print("[ok] portal: index.html + api-platform.html")

    # 依赖清单
    deploy_dir = os.path.join(PAYLOAD_DIR, "deploy")
    os.makedirs(deploy_dir)
    with open(os.path.join(deploy_dir, "requirements.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(REQUIREMENTS)
    print("[ok] deploy/requirements.txt (35 pins)")

    # 打 tar.gz
    if os.path.exists(OUT):
        os.remove(OUT)
    with tarfile.open(OUT, "w:gz") as tar:
        for name in sorted(os.listdir(PAYLOAD_DIR)):
            tar.add(os.path.join(PAYLOAD_DIR, name), arcname=name)

    n = sum(len(fs) for _, _, fs in os.walk(PAYLOAD_DIR))
    print(f"DONE {OUT} {os.path.getsize(OUT)/1024/1024:.1f} MB, {n} files")


if __name__ == "__main__":
    main()
