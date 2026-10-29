#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 ChemLearnWindows.exe

要点：
  · 后端 app 是"运行时从解压目录导入"的，PyInstaller 静态分析看不到其中的
    import（fastapi.middleware.cors 之类），因此必须用 --collect-submodules
    把 fastapi / starlette / uvicorn / passlib 全量子模块收进来。
  · 排除 pip/pytest/mypy/paramiko 等开发期依赖，既减小体积也大幅缩短构建时间。

用法：python build_win.py
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# 后端源码（payload 就是从它打包的），用来推导真正需要打进 exe 的模块
BACKEND_APP = os.path.join(
    os.path.dirname(os.path.dirname(HERE)), "化学", "01-源代码", "backend", "app")

COLLECT = ["fastapi", "starlette", "uvicorn", "passlib"]

FROM_RE = re.compile(r"^[ \t]*from[ \t]+([\w.]+)[ \t]+import[ \t]+\(?([^\n)]*)", re.M)
IMP_RE = re.compile(r"^[ \t]*import[ \t]+([\w., \t]+)", re.M)


def scan_imports(root):
    """扫描后端源码，返回所有被导入的模块路径（含子模块）。

    后端是在运行时从解压目录加载的，PyInstaller 静态分析看不到这些 import，
    所以必须把它们全部变成 --hidden-import，否则 exe 一启动就 ModuleNotFoundError。
    """
    mods = set()
    if not os.path.isdir(root):
        print("警告：找不到后端源码目录 %s，跳过自动扫描" % root)
        return mods
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                    src = f.read()
            except Exception:
                continue
            for m in FROM_RE.finditer(src):
                base = m.group(1).strip()
                if not base or base.startswith(".") or base.split(".")[0] == "app":
                    continue
                mods.add(base)
                for name in m.group(2).split(","):
                    name = name.strip().split(" as ")[0].strip()
                    if re.fullmatch(r"[A-Za-z_]\w*", name or ""):
                        mods.add(base + "." + name)
            for m in IMP_RE.finditer(src):
                for part in m.group(1).split(","):
                    path = part.strip().split(" as ")[0].strip()
                    if not path or path.startswith("."):
                        continue
                    if path.split(".")[0] == "app":
                        continue
                    mods.add(path)
    return mods


# 业务按需导入 / 可能会被上面扫描漏掉的
HIDDEN_EXTRA = [
    "sqlalchemy.ext.asyncio",
    "sqlalchemy.orm",
    "sqlalchemy.sql",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "aiosqlite",
    "greenlet",
    "bcrypt",
    "passlib.handlers.bcrypt",
    "jwt",
    "anyio",
    "anyio._backends._asyncio",
    "sniffio",
    "h11",
    "multipart",
    "python_multipart",
    "email_validator",
    "openpyxl.styles",
    "openpyxl.workbook",
    "openpyxl.worksheet.worksheet",
    "pypinyin",
    "PyPDF2",
    "xlrd",
    "psutil",
    "httpx",
    "httpcore",
    "redis",
    "dotenv",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]

EXCLUDE = [
    "pip", "wheel", "setuptools", "pkg_resources", "distutils",
    "pytest", "_pytest", "mypy", "hypothesis", "invoke",
    "docutils", "sphinx", "pygments", "IPython", "jedi",
    "tkinter", "numpy", "PIL", "matplotlib", "pandas", "scipy",
    "alembic", "gunicorn", "paramiko", "watchfiles", "watchgod", "uvloop",
]


# 后端启动必需、缺一个就起不来的包。构建前先自检，避免打出一个「一跑就 ModuleNotFoundError」的 exe
REQUIRED = [
    "fastapi", "starlette", "uvicorn", "sqlalchemy", "jwt",
    "passlib", "bcrypt", "aiosqlite", "greenlet", "pydantic",
    "pydantic_settings", "psutil", "multipart", "email_validator",
    "openpyxl", "httpx", "dotenv",
]


def main():
    import importlib.util
    missing = [m for m in REQUIRED if importlib.util.find_spec(m) is None]
    if missing:
        print("构建中止：当前解释器缺少运行期依赖 %s" % ", ".join(missing))
        print("  解释器：%s" % sys.executable)
        print("  先执行：%s -m pip install %s" % (sys.executable, " ".join(missing)))
        return 1

    scanned = scan_imports(BACKEND_APP)
    # 过滤掉 "from fastapi import APIRouter" 这类把类名当子模块的假阳性
    import importlib.util
    valid = set()
    for mod in scanned:
        try:
            if importlib.util.find_spec(mod) is not None:
                valid.add(mod)
        except Exception:
            pass
    hidden = sorted(set(HIDDEN_EXTRA) | valid)
    print("自动扫描到 %d 个导入模块，其中 %d 个是真实模块，合计 hidden-import %d 个"
          % (len(scanned), len(valid), len(hidden)))

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--console",
        "--name", "ChemLearnWindows",
        # 输出到新目录：避免覆盖旧产物时被安全删除钩子拦住
        "--distpath", "out",
        "--workpath", "build",
        "--add-data", "payload_chem.tar.gz;.",
    ]
    for m in COLLECT:
        args += ["--collect-submodules", m]
    for m in hidden:
        args += ["--hidden-import", m]
    for m in EXCLUDE:
        args += ["--exclude-module", m]
    args.append("win_runner.py")

    t0 = time.time()
    print("开始构建 ...", flush=True)
    rc = subprocess.call(args, cwd=HERE)
    cost = int(time.time() - t0)
    if rc != 0:
        print("构建失败 rc=%d（%ds）" % (rc, cost))
        return rc
    exe = os.path.join(HERE, "out", "ChemLearnWindows.exe")
    print("构建成功，用时 %d 分 %d 秒" % (cost // 60, cost % 60))
    print("产物：%s  (%.1f MB)" % (exe, os.path.getsize(exe) / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
