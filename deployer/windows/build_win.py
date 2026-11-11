#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 win_deployer.py + 运行时包打成一个 ChemLearnWindows.exe。

为什么需要 hidden-import：后端 app 是运行时从解压目录导入的，PyInstaller 静态
分析看不到 fastapi.middleware.cors、sqlalchemy.dialects.sqlite.aiosqlite 这类
动态导入，必须显式声明，否则 exe 一启动就 ModuleNotFoundError。

用法：
    python build_win.py                 # 用现有 payload_chem.tar.gz 打包
    python build_win.py --with-payload  # 先重新生成运行时包再打包
"""
import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BACKEND_APP = os.path.join(REPO, "backend", "app")

EXE_NAME = "ChemLearnWindows"
PAYLOAD = os.path.join(HERE, "payload_chem.tar.gz")
ICON = os.path.join(HERE, "app.ico")
VERSION_FILE = os.path.join(HERE, "win_version.txt")
OUT_DIR = os.path.join(HERE, "out")
WORK_DIR = os.path.join(HERE, "build")
DIST_EXE = os.path.join(OUT_DIR, EXE_NAME + ".exe")

# 运行时才被导入、静态分析扫不到的模块
HIDDEN_EXTRA = [
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.orm",
    "sqlalchemy.sql",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    "aiosqlite",
    "greenlet",
    "bcrypt",
    "passlib.handlers.bcrypt",
    "passlib.context",
    "jwt",
    "anyio",
    "anyio._backends._asyncio",
    "sniffio",
    "h11",
    "click",
    "multipart",
    "python_multipart",
    "dotenv",
    "pypinyin",
    "PyPDF2",
    "xlrd",
    "pymupdf",
    "openpyxl.styles",
    "openpyxl.workbook",
    "openpyxl.worksheet.worksheet",
    "openpyxl.cell._writer",
    "httpx",
    "httpcore",
    "psutil",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]

COLLECT_SUBMODULES = [
    "fastapi", "starlette", "uvicorn", "passlib", "sqlalchemy",
    "pydantic", "pydantic_settings", "openpyxl", "httpx",
    "dotenv", "multipart", "PyPDF2", "xlrd",
]

EXCLUDE = [
    "pip", "pytest", "_pytest", "mypy", "hypothesis", "invoke",
    "docutils", "sphinx", "IPython", "jedi", "tkinter.test",
    "numpy", "PIL", "matplotlib", "pandas", "scipy",
    "alembic", "gunicorn", "paramiko", "watchfiles", "watchdog",
    "uvloop", "websockets", "httptools", "yaml", "redis",
]

REQUIRED = [
    "fastapi", "starlette", "uvicorn", "sqlalchemy", "jwt", "passlib",
    "bcrypt", "aiosqlite", "greenlet", "pydantic", "pydantic_settings",
    "psutil", "multipart", "openpyxl", "httpx",
    "dotenv", "pypinyin", "PyPDF2", "xlrd", "fitz",
]

FROM_RE = re.compile(r"^[ \t]*from[ \t]+([\w.]+)[ \t]+import[ \t]+\(?([^\n)]*)", re.M)
IMP_RE = re.compile(r"^[ \t]*import[ \t]+([\w., \t]+)", re.M)


def scan_imports(root):
    """扫描后端源码里出现的模块，补进 hidden-import"""
    modules = set()
    if not os.path.isdir(root):
        print("警告：找不到后端源码 %s，跳过自动扫描" % root)
        return modules
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if not name.endswith(".py"):
                continue
            try:
                with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                    source = f.read()
            except Exception:
                continue
            for match in FROM_RE.finditer(source):
                base = match.group(1).strip()
                if not base or base.startswith(".") or base.split(".")[0] == "app":
                    continue
                modules.add(base)
                for item in match.group(2).split(","):
                    item = item.strip().split(" as ")[0].strip()
                    if re.fullmatch(r"[A-Za-z_]\w*", item or ""):
                        modules.add(base + "." + item)
            for match in IMP_RE.finditer(source):
                for part in match.group(1).split(","):
                    path = part.strip().split(" as ")[0].strip()
                    if not path or path.startswith("."):
                        continue
                    if path.split(".")[0] == "app":
                        continue
                    modules.add(path)
    return modules


def valid_modules(candidates):
    """过滤掉把类名当模块的假阳性"""
    valid = set()
    for module in candidates:
        try:
            if importlib.util.find_spec(module) is not None:
                valid.add(module)
        except Exception:
            continue
    return valid


def check_environment():
    missing = [name for name in REQUIRED if importlib.util.find_spec(name) is None]
    if importlib.util.find_spec("PyInstaller") is None:
        missing.append("PyInstaller")
    if missing:
        print("构建中止：当前解释器缺少 %s" % ", ".join(missing))
        print("  解释器：%s" % sys.executable)
        print("  建议用独立的构建环境：")
        print("    python -m venv deployer/windows/.buildenv")
        print("    deployer/windows/.buildenv/Scripts/python -m pip install "
              "-r deployer/windows/requirements-build.txt")
        return False
    for path in (PAYLOAD, ICON, VERSION_FILE):
        if not os.path.exists(path):
            print("缺少 %s" % path)
            if path == PAYLOAD:
                print("  先运行：python deployer/windows/build_payload.py")
            elif path == ICON:
                print("  先运行：python deployer/windows/make_icon.py")
            return False
    return True


def run_pyinstaller(hidden):
    os.makedirs(OUT_DIR, exist_ok=True)
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", EXE_NAME,
        "--icon", ICON,
        "--version-file", VERSION_FILE,
        "--distpath", OUT_DIR,
        "--workpath", WORK_DIR,
        "--specpath", WORK_DIR,
        "--add-data", "%s%s." % (PAYLOAD, os.pathsep),
        "--add-data", "%s%s." % (ICON, os.pathsep),
    ]
    for module in COLLECT_SUBMODULES:
        args += ["--collect-submodules", module]
    for module in sorted(hidden):
        args += ["--hidden-import", module]
    for module in EXCLUDE:
        args += ["--exclude-module", module]
    args.append(os.path.join(HERE, "win_deployer.py"))

    print("开始构建（hidden-import %d 个）…" % len(hidden))
    print(" ".join(args))
    started = time.time()
    code = subprocess.call(args, cwd=HERE)
    cost = int(time.time() - started)
    if code != 0:
        print("构建失败 rc=%d（%d 秒）" % (code, cost))
        return code
    size = os.path.getsize(DIST_EXE) / 1048576.0
    print("")
    print("构建成功：%s（%.1f MB，用时 %d 分 %d 秒）"
          % (DIST_EXE, size, cost // 60, cost % 60))
    return 0


def main():
    parser = argparse.ArgumentParser(description="打包 ChemLearnWindows.exe")
    parser.add_argument("--with-payload", action="store_true",
                        help="先用当前仓库重新生成 payload_chem.tar.gz")
    parser.add_argument("--fresh", action="store_true",
                        help="清理 build/out 后重新打包")
    args = parser.parse_args()

    if args.with_payload:
        code = subprocess.call([sys.executable, os.path.join(HERE, "build_payload.py")],
                               cwd=HERE)
        if code != 0:
            return code

    if args.fresh:
        for path in (WORK_DIR, OUT_DIR):
            shutil.rmtree(path, ignore_errors=True)

    if not check_environment():
        return 2

    scanned = scan_imports(BACKEND_APP)
    # 注意：不能过滤标准库。后端 app 是运行时从解压目录加载的，PyInstaller
    # 分析 win_deployer.py 时看不到 email.mime 这类标准库子模块，漏了就会
    # 在启动时报 ModuleNotFoundError。
    hidden = set(HIDDEN_EXTRA) | valid_modules(scanned)
    print("扫描到 %d 个导入，合并后 hidden-import %d 个" % (len(scanned), len(hidden)))
    return run_pyinstaller(hidden)


if __name__ == "__main__":
    sys.exit(main())
