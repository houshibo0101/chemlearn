#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""化学学习系统 · Windows 版运行器

双击启动：解压运行时文件到用户目录 → 启动本地服务 → 打开浏览器。
无需安装 Python、无需服务器，局域网内其它电脑也可访问。

用法：
  ChemLearnWindows.exe                 默认 8000 端口，自动打开浏览器
  ChemLearnWindows.exe --port 8090     指定端口
  ChemLearnWindows.exe --no-browser    不自动打开浏览器
  ChemLearnWindows.exe --reset         重新解压运行时（题库重置为内置版本）
"""
import argparse
import importlib
import os
import shutil
import socket
import sys
import tarfile
import threading
import time
import urllib.request
import webbrowser

# 预导入运行时依赖：后端 app 是运行时从解压目录加载的，
# PyInstaller 静态分析看不到，这里显式导入以确保被完整打包
import fastapi  # noqa: F401
import starlette  # noqa: F401
import sqlalchemy  # noqa: F401
import sqlalchemy.ext.asyncio  # noqa: F401
import aiosqlite  # noqa: F401
import greenlet  # noqa: F401
import pydantic  # noqa: F401
import pydantic_settings  # noqa: F401
import passlib  # noqa: F401
import passlib.context  # noqa: F401
import bcrypt  # noqa: F401
import jwt  # noqa: F401
import openpyxl  # noqa: F401
import psutil  # noqa: F401
import multipart  # noqa: F401
import email_validator  # noqa: F401
import httpx  # noqa: F401
import dotenv  # noqa: F401

VERSION = "1.0.2"
APP_NAME = "ChemLearnWindows"
# 前端产物把资源与接口路径硬编码为 /chem/...，本机运行没有 nginx 去前缀，
# 因此用中间件把 /chem/xxx 改写成 /xxx（前端零改动，与线上行为一致）
URL_PREFIX = "/chem"
WEB_PATH = URL_PREFIX + "/app/"
DATA_ROOT = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), APP_NAME)
MARKER = os.path.join(DATA_ROOT, ".extracted")
BACKEND_DIR = os.path.join(DATA_ROOT, "化学", "backend")


def res_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


PAYLOAD = res_path("payload_chem.tar.gz")


def log(msg):
    try:
        print(msg, flush=True)
    except Exception:
        pass   # 控制台编码不支持中文时不至于直接崩溃


def _payload_fingerprint():
    """用「版本号 + payload 大小/时间」当指纹，换了新 exe 就能识别出来。"""
    try:
        st = os.stat(PAYLOAD)
        return "%s-%d-%d" % (VERSION, st.st_size, int(st.st_mtime))
    except OSError:
        return VERSION


def extract_payload(force=False):
    fp = _payload_fingerprint()
    try:
        with open(MARKER, encoding="utf-8") as f:
            marker_fp = f.read().strip()
    except OSError:
        marker_fp = ""

    first_run = not os.path.isdir(BACKEND_DIR)
    if not force and not first_run and marker_fp == fp:
        return

    if force:
        for name in ("化学", "portal", "deploy", ".extracted"):
            p = os.path.join(DATA_ROOT, name)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        log("按 --reset 清空运行时目录，重新解压 ...")
    elif first_run:
        log("首次运行，正在解压运行时文件（约 2 秒）...")
    else:
        # 升级：清掉旧前端产物（文件名带哈希，不换会一直用旧 UI），数据库原样保留
        shutil.rmtree(os.path.join(DATA_ROOT, "化学", "web"), ignore_errors=True)
        log("检测到新版本，正在更新运行时文件（数据库保留）...")

    os.makedirs(DATA_ROOT, exist_ok=True)
    db_path = os.path.join(DATA_ROOT, "化学", "backend", "chemlearn.db")
    with tarfile.open(PAYLOAD, "r:gz") as tar:
        for m in tar.getmembers():
            # 升级时不覆盖已有的数据库，避免把用户题库清成种子数据
            if not force and m.name.endswith("化学/backend/chemlearn.db") and os.path.exists(db_path):
                continue
            try:
                tar.extract(m, DATA_ROOT, filter="data")  # py3.12+ 安全解压
            except TypeError:
                tar.extract(m, DATA_ROOT)
    with open(MARKER, "w", encoding="utf-8") as f:
        f.write(fp)
    log("解压完成：" + DATA_ROOT)


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def find_port(preferred):
    for p in range(preferred, preferred + 40):
        if port_free(p):
            return p
    return preferred


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def wait_and_open(port, no_browser):
    url = "http://127.0.0.1:%d%s" % (port, WEB_PATH)
    deadline = time.time() + 40
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/health" % port, timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.6)
    log("")
    log("=" * 66)
    log("  化学学习系统已启动")
    log("  本机访问：  " + url)
    log("  局域网访问：" + "http://%s:%d%s" % (lan_ip(), port, WEB_PATH))
    log("  管理账号：  admin / admin123（请登录后修改密码）")
    log("  停止服务：  关闭本窗口，或按 Ctrl+C")
    log("  数据目录：  " + DATA_ROOT)
    log("=" * 66)
    log("")
    if not no_browser:
        webbrowser.open(url)


def build_app(app):
    """包装 ASGI 应用：
    1) /chem/xxx -> /xxx（前端硬编码前缀，本机没有 nginx 做去前缀转发）
    2) / -> 302 到 /chem/app/（方便只输 IP:端口）
    """
    from starlette.requests import Request
    from starlette.responses import RedirectResponse

    async def wrapped(scope, receive, send):
        if scope.get("type") not in ("http", "websocket"):
            await app(scope, receive, send)
            return
        path = scope.get("path", "") or "/"
        if path == "/":
            req = Request(scope)
            resp = RedirectResponse(WEB_PATH, status_code=302)
            await resp(req.scope, receive, send)
            return
        if path == URL_PREFIX or path.startswith(URL_PREFIX + "/"):
            scope = dict(scope)
            new_path = path[len(URL_PREFIX):] or "/"
            scope["path"] = new_path
            scope["raw_path"] = new_path.encode("utf-8")
        await app(scope, receive, send)

    return wrapped


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    log("")
    log("  化学学习系统 · Windows 版  v" + VERSION)
    log("  " + "-" * 60)

    if not os.path.exists(PAYLOAD):
        log("错误：缺少内嵌运行时包 payload_chem.tar.gz")
        input("按回车退出...")
        sys.exit(2)

    extract_payload(force=args.reset)

    # 关键：切换工作目录并加入搜索路径，后端按相对路径找数据库与前端
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, BACKEND_DIR)

    # 后端 DEBUG=True 会把每条 SQL 打到控制台，窗口里太吵，这里静音
    import logging
    for name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool"):
        logging.getLogger(name).setLevel(logging.WARNING)

    import uvicorn
    from app.main import app  # noqa: E402

    # create_async_engine(echo=settings.DEBUG) 会在建引擎时强制打开 INFO 级别，
    # 必须在导入之后把它关掉
    try:
        from app.core import database as _db
        for _name in ("engine", "async_engine"):
            _eng = getattr(_db, _name, None)
            if _eng is not None:
                _eng.echo = False
    except Exception:
        pass
    for name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
        logging.getLogger(name).setLevel(logging.WARNING)

    app = build_app(app)

    port = find_port(args.port)
    if port != args.port:
        log("端口 %d 已被占用，自动改用 %d" % (args.port, port))

    threading.Thread(target=wait_and_open, args=(port, args.no_browser), daemon=True).start()

    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        pass
    except BaseException:
        # 双击运行时窗口会自动关闭，这里暂停一下让用户看清错误
        import traceback
        traceback.print_exc()
        try:
            input("\n启动失败，请把上面的错误信息截图反馈。按回车键退出...")
        except Exception:
            pass
        sys.exit(1)
