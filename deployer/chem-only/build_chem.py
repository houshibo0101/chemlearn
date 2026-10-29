# -*- coding: utf-8 -*-
"""从六学科部署器派生「纯化学版」：
  - payload_chem.tar.gz：只含化学（backend/app + chemlearn.db + web/dist/app）+ api-platform.html + requirements
  - deployer_chem.py：SUBJECTS 仅 chem、单 nginx 站点（根路径 301 → /chem/app/）、界面改化学主题
"""
import os
import shutil
import tarfile

BASE = r"D:/学习中心/部署工具"
CHEM = os.path.join(BASE, "chem-only")
ASSETS = os.path.join(BASE, "assets")
PAYLOAD_DIR = os.path.join(CHEM, "payload")
OUT_TGZ = os.path.join(CHEM, "payload_chem.tar.gz")

REQUIREMENTS_SRC = os.path.join(BASE, "payload", "deploy", "requirements.txt")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "node_modules", ".venv")


def build_payload():
    if os.path.exists(PAYLOAD_DIR):
        shutil.rmtree(PAYLOAD_DIR)
    os.makedirs(PAYLOAD_DIR)

    src_root = r"D:/学习中心/化学/01-源代码"
    shutil.copytree(os.path.join(src_root, "backend", "app"),
                    os.path.join(PAYLOAD_DIR, "化学", "backend", "app"), ignore=IGNORE)
    shutil.copy2(os.path.join(ASSETS, "dbs", "chemlearn.db"),
                 os.path.join(PAYLOAD_DIR, "化学", "backend", "chemlearn.db"))
    shutil.copytree(os.path.join(src_root, "web", "dist", "app"),
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
    with tarfile.open(OUT_TGZ, "w:gz") as tar:
        for name in sorted(os.listdir(PAYLOAD_DIR)):
            tar.add(os.path.join(PAYLOAD_DIR, name), arcname=name)
    n = sum(len(fs) for _, _, fs in os.walk(PAYLOAD_DIR))
    print(f"DONE {OUT_TGZ} {os.path.getsize(OUT_TGZ)/1024/1024:.1f} MB, {n} files")


# ============================================================ 派生 deployer_chem.py

def derive_deployer():
    src = os.path.join(BASE, "deployer.py")
    with open(src, encoding="utf-8") as f:
        t = f.read()

    reps = [
        # 版本与包名
        ('VERSION = "1.2.0"', 'VERSION = "1.0.0"'),
        ('PAYLOAD_PATH = res_path("payload.tar.gz")', 'PAYLOAD_PATH = res_path("payload_chem.tar.gz")'),
        # 仅化学
        ('''SUBJECTS = [("chem", "化学"), ("math", "数学"), ("phys", "物理"),
            ("bio", "生物"), ("chn", "语文"), ("eng", "英语")]''',
         'SUBJECTS = [("chem", "化学")]'),
        # nginx：单学科时根路径 301 到学科应用
        ('''        loc = []
        for i, (key, _) in enumerate(SUBJECTS):''',
         '''        loc = []
        if len(SUBJECTS) == 1:
            loc.append("    location = / { return 301 /%s/app/; }" % SUBJECTS[0][0])
        for i, (key, _) in enumerate(SUBJECTS):'''),
        # 门户只拷 api-platform.html
        ('cp -f "@@ROOT@@/portal/index.html" "@@ROOT@@/portal/api-platform.html" @@PORTAL_ROOT@@/',
         'cp -f "@@ROOT@@/portal/api-platform.html" @@PORTAL_ROOT@@/'),
        ('echo "[OK] 六学科源码 + 数据库 + 门户已就位"',
         'echo "[OK] 化学源码 + 数据库 + API 开放平台页已就位"'),
        # 门户健康检查跟随 301
        ('if curl -sf -m 5 "http://127.0.0.1:@@NGINX_PORT@@/" >/dev/null; then\n  echo "[OK] 门户页面可访问"',
         'if curl -sfL -m 5 "http://127.0.0.1:@@NGINX_PORT@@/" >/dev/null; then\n  echo "[OK] 站点可访问（根路径已跳转化学应用）"'),
        # 访问地址：化学应用 + API 平台
        ('''            urls = [base + "/"]
            urls += [base + "/%s/app/" % k for k, _ in SUBJECTS]
            urls.append(base + "/api-platform.html")''',
         '''            urls = [base + "/%s/app/" % k for k, _ in SUBJECTS]
            urls.append(base + "/api-platform.html")'''),
        # 文案
        ('学习中心 · 一键部署', '化学学习系统 · 一键部署'),
        ('STUDY CENTER DEPLOYER', 'CHEM LEARN DEPLOYER'),
        ('在一台全新的 Ubuntu 服务器上，自动完成六学科学习系统的完整部署<br>源码 · 题库数据库 · 门户官网 · 开机自启 —— 全程无需手动登录服务器',
         '在一台全新的 Ubuntu 服务器上，自动完成化学学习系统的完整部署<br>源码 · 题库数据库 · API 开放平台 · 开机自启 —— 全程无需手动登录服务器'),
        ('''      <span class="chip">🧪 化学</span><span class="chip">📐 数学</span><span class="chip">🧭 物理</span>
      <span class="chip">🧬 生物</span><span class="chip">📖 语文</span><span class="chip">🔤 英语</span>''',
         '''      <span class="chip">🧪 化学</span>'''),
        ("const ICONS=['🏫','🧪','📐','🧭','🧬','📖','🔤','🛠️'];",
         "const ICONS=['🧪','🛠️'];"),
        ("const NAMES=['门户官网','化学','数学','物理','生物','语文','英语','API 开放平台'];",
         "const NAMES=['化学学习应用','API 开放平台'];"),
        ('整套六学科学习系统已上线，点击卡片即可访问', '化学学习系统已上线，点击卡片即可访问'),
        ('内嵌完整部署包：六学科源码 · 前端页面 · 题库数据库 · 门户官网 · 依赖锁定',
         '内嵌完整部署包：化学学科源码 · 前端页面 · 题库数据库 · 依赖锁定'),
        # 文档头
        ('内嵌 payload.tar.gz 包含：六学科后端源码 + 前端构建产物 +\n干净数据库(题库) + 门户官网 + 依赖锁定清单。',
         '内嵌 payload_chem.tar.gz 包含：化学后端源码 + 前端构建产物 +\n干净数据库(题库) + API 开放平台页 + 依赖锁定清单。'),
        ('即可自动完成整套六学科学习系统的部署：', '即可自动完成化学学习系统的部署：'),
        ('AI 已写入各学科 backend/.env：模型 %s（套卷生成 / AI 问答可直接用）',
         'AI 已写入 backend/.env：模型 %s（套卷生成 / AI 问答可直接用）'),
    ]

    for old, new in reps:
        if old not in t:
            raise SystemExit("替换目标未找到：\n" + old[:120])
        t = t.replace(old, new)

    out = os.path.join(CHEM, "deployer_chem.py")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    print("[ok] 派生 deployer_chem.py")


if __name__ == "__main__":
    build_payload()
    derive_deployer()
