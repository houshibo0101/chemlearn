# -*- coding: utf-8 -*-
"""重新生成 windows/payload_chem.tar.gz（含最新前端构建产物）"""
import os
import shutil
import tarfile

BASE = r"D:/学习中心/部署工具"
SRC = r"D:/学习中心/化学/01-源代码"
OUT = os.path.join(BASE, "windows", "payload_chem.tar.gz")
STAGE = os.path.join(BASE, "windows", "_payload_stage")
REQ = os.path.join(BASE, "payload", "deploy", "requirements.txt")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "node_modules", ".venv")

if os.path.exists(STAGE):
    shutil.rmtree(STAGE)
os.makedirs(STAGE)

shutil.copytree(os.path.join(SRC, "backend", "app"),
                os.path.join(STAGE, "化学", "backend", "app"), ignore=IGNORE)
shutil.copy2(os.path.join(BASE, "assets", "dbs", "chemlearn.db"),
             os.path.join(STAGE, "化学", "backend", "chemlearn.db"))
shutil.copytree(os.path.join(SRC, "web", "dist", "app"),
                os.path.join(STAGE, "化学", "web", "dist", "app"), ignore=IGNORE)
os.makedirs(os.path.join(STAGE, "portal"))
shutil.copy2(os.path.join(BASE, "assets", "portal", "api-platform.html"),
             os.path.join(STAGE, "portal", "api-platform.html"))
os.makedirs(os.path.join(STAGE, "deploy"))
shutil.copy2(REQ, os.path.join(STAGE, "deploy", "requirements.txt"))

if os.path.exists(OUT):
    os.remove(OUT)
with tarfile.open(OUT, "w:gz") as tar:
    for name in sorted(os.listdir(STAGE)):
        tar.add(os.path.join(STAGE, name), arcname=name)

n = sum(len(fs) for _, _, fs in os.walk(STAGE))
print("DONE %s %.1f MB, %d files" % (OUT, os.path.getsize(OUT) / 1048576, n))
shutil.rmtree(STAGE, ignore_errors=True)
