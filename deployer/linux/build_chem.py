# -*- coding: utf-8 -*-
"""构建「纯化学版」部署包 payload_chem.tar.gz。

产物内容：化学 backend/app + chemlearn.db + web/dist/app + api-platform.html + requirements。
同目录的 deployer_chem.py 是由 deployer.py 派生的化学专用部署器（已随仓库提供）：
SUBJECTS 仅 chem、单 nginx 站点（根路径 301 → /chem/app/）、界面为化学主题。

运行前提（仓库内不含这些文件，需本地自备）：
  1. 前端已构建：        cd web && npm install && npm run build   → 生成 web/dist/app
  2. 干净数据库与门户页：环境变量 SC_ASSETS 指向一个目录，内含
                            dbs/chemlearn.db
                            portal/api-platform.html
  3. 依赖清单：环境变量 SC_REQUIREMENTS 指向 requirements.txt
                （默认取 backend/requirements.txt）

用法：
  SC_ASSETS=/path/to/assets python deployer/linux/build_chem.py
"""
import os
import shutil
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))            # deployer/linux
REPO = os.path.dirname(os.path.dirname(HERE))                # 仓库根

SRC_ROOT = os.path.join(REPO, "backend")                     # 化学后端
WEB_DIST = os.path.join(REPO, "web", "dist", "app")           # 前端构建产物

ASSETS = os.environ.get("SC_ASSETS", "").strip()
REQUIREMENTS_SRC = os.environ.get("SC_REQUIREMENTS", "").strip() \
    or os.path.join(REPO, "backend", "requirements.txt")

OUT_DIR = os.path.join(HERE, "build")
PAYLOAD_DIR = os.path.join(OUT_DIR, "payload")
OUT_TGZ = os.path.join(HERE, "payload_chem.tar.gz")

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "node_modules", ".venv")


def check_prereq():
    missing = []
    if not os.path.isdir(os.path.join(SRC_ROOT, "app")):
        missing.append("backend/app（化学后端源码）")
    if not os.path.isdir(WEB_DIST):
        missing.append("web/dist/app（先执行 npm run build）")
    if not ASSETS or not os.path.isfile(os.path.join(ASSETS, "dbs", "chemlearn.db")):
        missing.append("$SC_ASSETS/dbs/chemlearn.db（干净题库数据库）")
    if not ASSETS or not os.path.isfile(os.path.join(ASSETS, "portal", "api-platform.html")):
        missing.append("$SC_ASSETS/portal/api-platform.html（API 开放平台页）")
    if not os.path.isfile(REQUIREMENTS_SRC):
        missing.append("requirements.txt（可用 $SC_REQUIREMENTS 指定）")
    if missing:
        print("缺少以下前置文件：")
        for m in missing:
            print("  - " + m)
        sys.exit(2)


def build_payload():
    if os.path.exists(PAYLOAD_DIR):
        shutil.rmtree(PAYLOAD_DIR)
    os.makedirs(PAYLOAD_DIR)

    shutil.copytree(os.path.join(SRC_ROOT, "app"),
                    os.path.join(PAYLOAD_DIR, "化学", "backend", "app"), ignore=IGNORE)
    shutil.copy2(os.path.join(ASSETS, "dbs", "chemlearn.db"),
                 os.path.join(PAYLOAD_DIR, "化学", "backend", "chemlearn.db"))
    shutil.copytree(WEB_DIST,
                    os.path.join(PAYLOAD_DIR, "化学", "web", "dist", "app"), ignore=IGNORE)
    print("[ok] 化学: app + chemlearn.db + dist")

    portal = os.path.join(PAYLOAD_DIR, "portal")
    os.makedirs(portal)
    shutil.copy2(os.path.join(ASSETS, "portal", "api-platform.html"), portal)
    print("[ok] portal: api-platform.html（六学科首页不放，根路径改为跳转化学应用）")

    dep = os.path.join(PAYLOAD_DIR, "deploy")
    os.makedirs(dep)
    shutil.copy2(REQUIREMENTS_SRC, os.path.join(dep, "requirements.txt"))
    print("[ok] deploy/requirements.txt")

    if os.path.exists(OUT_TGZ):
        os.remove(OUT_TGZ)


def pack():
    total = 0
    files = 0
    with tarfile.open(OUT_TGZ, "w:gz") as tar:
        for root, _dirs, names in os.walk(PAYLOAD_DIR):
            for n in names:
                p = os.path.join(root, n)
                tar.add(p, arcname=os.path.relpath(p, PAYLOAD_DIR))
                total += os.path.getsize(p)
                files += 1
    print("[ok] 打包 %s（%d 个文件，%.1f MB）"
          % (os.path.basename(OUT_TGZ), files, os.path.getsize(OUT_TGZ) / 1048576.0))


def main():
    check_prereq()
    build_payload()
    pack()
    print("完成。下一步：")
    print("  Linux   : python deployer/linux/deployer_chem.py --host <ip> --user root --password ***")
    print("  Windows : 把 payload_chem.tar.gz 放到 deployer/windows/ 下，再运行 build_win.py")


if __name__ == "__main__":
    main()
