#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学习中心 · 一键部署工具

双击运行后自动打开浏览器界面（本机 127.0.0.1），
输入一台全新 Ubuntu/Debian 服务器的 IP / 用户名 / 密码，
即可自动完成整套六学科学习系统的部署：
  上传内嵌部署包 -> apt 安装 nginx/python -> venv + pip 依赖
  -> 6 个 systemd 服务(开机自启) -> nginx 门户 + 子路径反代
  -> 深链接/健康检查 -> 输出访问地址

内嵌 payload.tar.gz 包含：六学科后端源码 + 前端构建产物 +
干净数据库(题库) + 门户官网 + 依赖锁定清单。

命令行（无界面）模式：
  deployer.exe --headless --host 1.2.3.4 --user root --password xxx [--test-mode]
  deployer.exe --headless --host 1.2.3.4 --user root --password xxx --cleanup   # 清理 --test-mode 部署
  deployer.py --no-browser    # 启动界面服务但不自动打开浏览器（预览/调试用）
"""
import json
import os
import sys
import threading
import time
import tarfile
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.2.0"

SUBJECTS = [("chem", "化学"), ("math", "数学"), ("phys", "物理"),
            ("bio", "生物"), ("chn", "语文"), ("eng", "英语")]
PROD_PORTS = {"chem": 8000, "math": 8001, "phys": 8002,
              "bio": 8003, "chn": 8004, "eng": 8005}


def res_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


PAYLOAD_PATH = res_path("payload.tar.gz")

# ============================================================ 模板

UNIT_TEMPLATE = """[Unit]
Description=StudyCenter - @@SUBJECT@@ (port @@PORT@@)
After=network.target

[Service]
User=@@USER@@
WorkingDirectory=@@ROOT@@/@@SUBJECT@@/backend
ExecStart=@@VENV@@/bin/uvicorn app.main:app --host 0.0.0.0 --port @@PORT@@
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""

NGINX_TEMPLATE = """server {
    listen @@NGINX_PORT@@@@DEFAULT_SERVER@@;
    listen [::]:@@NGINX_PORT@@@@DEFAULT_SERVER@@;
    server_name _;
    root @@PORTAL_ROOT@@;
    index index.html;

    client_max_body_size 50m;
    proxy_read_timeout 300s;
    proxy_connect_timeout 10s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

@@LOCATION_BLOCK@@
    location / {
        try_files $uri $uri/ =404;
    }
}
"""

SETUP_SH = r'''#!/usr/bin/env bash
set -e
export DEBIAN_FRONTEND=noninteractive
STEP=0; TOTAL=7
step(){ STEP=$((STEP+1)); echo "==== [步骤 $STEP/$TOTAL] $1 ===="; }

step "安装系统依赖 (nginx / python3-venv / curl)"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq || echo "apt update 有警告，继续"
  apt-get install -y nginx python3-venv python3-pip curl >/dev/null
else
  echo "[FAIL] 仅支持 Ubuntu / Debian (apt)"; exit 30
fi
echo "[OK] 系统依赖就绪"

step "防火墙检查 (ufw 放行 Web 端口 @@NGINX_PORT@@)"
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow @@NGINX_PORT@@/tcp >/dev/null && echo "[OK] ufw 已放行 @@NGINX_PORT@@/tcp"
else
  echo "ufw 未启用，跳过（云服务器请在安全组放行 @@NGINX_PORT@@ 端口）"
fi

step "解压部署包到 @@ROOT@@"
rm -rf "@@ROOT@@"
mkdir -p "@@ROOT@@"
tar -xzf /tmp/sc_deploy/payload.tar.gz -C "@@ROOT@@"
mkdir -p @@PORTAL_ROOT@@
cp -f "@@ROOT@@/portal/index.html" "@@ROOT@@/portal/api-platform.html" @@PORTAL_ROOT@@/
chown -R @@USER@@ "@@ROOT@@" @@PORTAL_ROOT@@ 2>/dev/null || true
echo "[OK] 六学科源码 + 数据库 + 门户已就位"

@@WRITE_ENV@@

step "创建 Python 虚拟环境"
rm -rf "@@VENV@@"
@@SUDO_U@@ python3 -m venv "@@VENV@@"
echo "[OK] 虚拟环境: @@VENV@@"

step "安装 Python 依赖 (首次约 1-3 分钟，请耐心等待)"
MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"
if ! @@SUDO_U@@ "@@VENV@@/bin/pip" install --progress-bar off --disable-pip-version-check -r "@@ROOT@@/deploy/requirements.txt" -i $MIRROR; then
  echo "清华镜像安装失败，改用官方源重试..."
  @@SUDO_U@@ "@@VENV@@/bin/pip" install --progress-bar off --disable-pip-version-check -r "@@ROOT@@/deploy/requirements.txt"
fi
echo "[OK] Python 依赖安装完成"

step "注册 systemd 服务 (开机自启) 并配置 nginx"
systemctl daemon-reload
for U in /tmp/sc_deploy/units/*.service; do cp -f "$U" /etc/systemd/system/; done
systemctl daemon-reload
@@ENABLE_CMDS@@
cp -f /tmp/sc_deploy/nginx-site.conf @@NGINX_SITE@@
ln -sf @@NGINX_SITE@@ /etc/nginx/sites-enabled/$(basename @@NGINX_SITE@@)
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx 2>/dev/null || systemctl restart nginx
@@START_CMDS@@
echo "[OK] 服务已启动"

step "健康检查"
echo "等待服务启动（每个端口最长等待 40 秒）..."
FAIL=0
for P in @@PORTS@@; do
  OKP=0
  for i in $(seq 1 20); do
    if curl -sf -m 3 "http://127.0.0.1:$P/api/health" >/dev/null; then OKP=1; break; fi
    sleep 2
  done
  if [ "$OKP" = "1" ]; then echo "[OK] 后端端口 $P 健康"; else echo "[FAIL] 后端端口 $P 未响应"; FAIL=1; fi
done
if curl -sf -m 5 "http://127.0.0.1:@@NGINX_PORT@@/" >/dev/null; then
  echo "[OK] 门户页面可访问"
else
  echo "[FAIL] 门户页面不可访问"; FAIL=1
fi
@@DEEPLINK_CHECKS@@
echo "==== 部署流程结束 ===="
if [ "$FAIL" = "1" ]; then echo "RESULT: PARTIAL"; else echo "RESULT: SUCCESS"; fi
'''

CLEANUP_SH = r'''#!/usr/bin/env bash
set -e
echo "==== 清理测试部署 ===="
systemctl disable --now @@UNITS@@ >/dev/null 2>&1 || true
rm -f /etc/systemd/system/@@PREFIX@@-*.service
rm -f /etc/nginx/sites-enabled/@@SITE_NAME@@ /etc/nginx/sites-available/@@SITE_NAME@@
systemctl daemon-reload
nginx -t >/dev/null 2>&1 && systemctl reload nginx || true
rm -rf "@@ROOT@@" "@@PORTAL_ROOT@@" /tmp/sc_deploy
echo "CLEANUP_DONE"
'''

# ============================================================ 日志

class Logger:
    def __init__(self):
        self._lines = []
        self._lock = threading.Lock()

    def add(self, text, level="info"):
        with self._lock:
            for ln in str(text).splitlines() or [""]:
                self._lines.append({"t": ln, "lv": level})

    def snapshot(self, since=0):
        with self._lock:
            return {"lines": self._lines[since:], "total": len(self._lines)}


LOG = Logger()
STATE = {"running": False, "ok": None, "urls": None}


# ============================================================ 部署器

class Deployer:
    def __init__(self, cfg, test_mode=False, keep=False):
        self.host = cfg["host"].strip()
        self.ssh_port = int(cfg.get("ssh_port") or 22)
        self.user = cfg["user"].strip() or "root"
        self.password = cfg["password"]
        self.test_mode = test_mode
        self.keep = keep
        self.client = None
        self.sftp = None
        # 部署参数
        if test_mode:
            self.prefix = "sctest"
            self.base_port = 9000
            self.nginx_port = 8081
            self.default_server = ""
            self.site_name = "sctest.conf"
        else:
            self.prefix = "study"
            self.base_port = 8000
            self.nginx_port = 80
            self.default_server = " default_server"
            self.site_name = "studycenter.conf"
        self.ports = {k: self.base_port + i for i, (k, _) in enumerate(SUBJECTS)}
        # 自定义 Web 访问端口（默认 80 / 测试模式 8081）
        try:
            wp = int(str(cfg.get("web_port") or "").strip() or self.nginx_port)
            if 1 <= wp <= 65535:
                self.nginx_port = wp
        except Exception:
            pass

        # AI 配置：部署时直接写进各学科 backend/.env，装完即可用
        self.ai_key = (cfg.get("ai_key") or "").strip()
        self.ai_base = (cfg.get("ai_base") or "").strip() or "https://ark.cn-beijing.volces.com/api/v3"
        self.ai_model = (cfg.get("ai_model") or "").strip() or "doubao-seed-2-0-mini-260428"
        self.ai_explain = (cfg.get("ai_explain_model") or "").strip()

    # ---------- AI 配置 ----------
    def env_text(self):
        """生成 .env 内容。

        注意：不要写 DEBUG=false —— 那会触发「默认 SECRET_KEY / admin123」的启动拦截，
        服务直接起不来。
        """
        lines = [
            "# 由部署器生成（改动后需重启服务生效）",
            "AI_API_KEY=" + self.ai_key,
            "AI_API_BASE=" + self.ai_base,
            "AI_MODEL=" + self.ai_model,
        ]
        if self.ai_explain:
            lines.append("AI_EXPLAIN_MODEL=" + self.ai_explain)
        lines.append("AI_TIMEOUT=180")
        return "\n".join(lines) + "\n"

    def env_shell(self, root):
        """setup.sh 里执行的一段：给每个学科的 backend 写 .env

        注意目录用的是学科中文名（化学/数学/...），不是 key（chem/math/...），
        与 systemd 的 WorkingDirectory 保持一致。
        """
        if not self.ai_key:
            return 'echo "[i] 未填写 AI Key，跳过 .env（部署后 AI 功能不可用）"'
        body = self.env_text()
        cmds = []
        for _key, sub in SUBJECTS:
            cmds.append(
                "mkdir -p '%s/%s/backend'\ncat > '%s/%s/backend/.env' <<'SCENVEOF'\n%sSCENVEOF\n"
                "chown %s '%s/%s/backend/.env' 2>/dev/null || true"
                % (root, sub, root, sub, body, self.user, root, sub)
            )
        cmds.append('echo "[OK] AI 配置已写入 %d 个学科的 .env（模型 %s）"' % (len(SUBJECTS), self.ai_model))
        return "\n".join(cmds)

    # ---------- 基础 ----------
    def log(self, msg, level="info"):
        LOG.add(msg, level)

    def connect(self):
        import paramiko
        candidates = [self.user] if self.user == "root" else [self.user, "root"]
        last_err = None
        for u in candidates:
            try:
                self.log(f"连接 {self.host}:{self.ssh_port} (用户 {u}) ...")
                cli = paramiko.SSHClient()
                cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                cli.connect(self.host, self.ssh_port, u, self.password,
                            timeout=12, banner_timeout=12, auth_timeout=12,
                            look_for_keys=False, allow_agent=False)
                self.client = cli
                self.user = u
                self.sftp = cli.open_sftp()
                self.log(f"[OK] 已连接（登录用户：{u}）", "ok")
                return
            except Exception as e:
                last_err = e
                self.log(f"  用户 {u} 连接失败：{e}", "info")
        raise RuntimeError(f"无法连接服务器：{last_err}")

    def close(self):
        try:
            if self.sftp:
                self.sftp.close()
            if self.client:
                self.client.close()
        except Exception:
            pass

    def _is_root(self):
        return self.exec_out("whoami").strip() == "root"

    def exec_out(self, cmd, timeout=30):
        _, out, _ = self.client.exec_command(cmd, timeout=timeout)
        return out.read().decode("utf-8", "replace")

    def used_ports(self):
        """远端已监听端口集合（用于自动挑选空闲端口）"""
        out = self.exec_out("ss -ltn 2>/dev/null | awk 'NR>1{print $4}' || true")
        used = set()
        for tok in out.split():
            if ":" in tok:
                tail = tok.rsplit(":", 1)[-1]
                if tail.isdigit():
                    used.add(int(tail))
        return used

    def pick_free_port(self, preferred, avoid=None):
        avoid = set(avoid or []) | {self.nginx_port}
        used = self.used_ports()
        for p in range(preferred, preferred + 30):
            if p not in used and p not in avoid:
                return p
        return preferred

    def sudo_out(self, cmd, timeout=30):
        """以 root 权限执行命令并返回输出（不需要流式日志时用）"""
        import shlex
        if getattr(self, "is_root", False):
            return self.exec_out(cmd, timeout=timeout)
        stdin, stdout, _ = self.client.exec_command(
            "sudo -S -p '' bash -c " + shlex.quote(cmd), timeout=timeout)
        stdin.write(self.password + "\n")
        stdin.flush()
        out = stdout.read().decode("utf-8", "replace")
        stdout.channel.recv_exit_status()
        return out

    def ensure_sudo(self):
        self.is_root = self._is_root()
        if self.is_root:
            self.sudo_u = ""
            self.log("当前为 root 用户，直接部署", "info")
            return
        # 验证 sudo
        stdin, stdout, _ = self.client.exec_command("sudo -S -p '' true", timeout=15)
        stdin.write(self.password + "\n")
        stdin.flush()
        rc = stdout.channel.recv_exit_status()
        if rc != 0:
            raise RuntimeError("sudo 验证失败：该用户需要有 sudo 权限，且密码正确")
        self.sudo_u = "sudo -u %s" % self.user
        self.log(f"[OK] sudo 验证通过（部署文件归 {self.user} 所有）", "ok")

    def check_os(self):
        rel = self.exec_out("cat /etc/os-release 2>/dev/null | grep -E '^(ID|VERSION_ID)=' || true")
        self.log("系统信息：" + rel.replace("\n", "  ").strip() if rel.strip() else "未知系统（将继续尝试）")
        if "ubuntu" not in rel and "debian" not in rel:
            self.log("[FAIL] 未检测到 Ubuntu/Debian，自动部署仅支持这两类系统", "fail")
            raise RuntimeError("目标系统不是 Ubuntu/Debian")

    # ---------- 远程脚本执行（流式日志） ----------
    def run_script(self, path, timeout=1500):
        if self.is_root:
            cmd = "bash %s" % path
        else:
            cmd = "sudo -S -p '' bash %s" % path
        stdin, stdout, _ = self.client.exec_command(cmd, timeout=timeout, get_pty=True)
        if not self.is_root:
            stdin.write(self.password + "\n")
            stdin.flush()
        tail = []
        for line in iter(stdout.readline, ""):
            line = line.rstrip("\r\n")
            if not line:
                continue
            tail.append(line)
            tail = tail[-60:]
            lv = "info"
            if line.startswith("===="):
                lv = "step"
            elif "[OK]" in line:
                lv = "ok"
            elif "[FAIL]" in line or "ERROR" in line or "error:" in line.lower():
                lv = "fail"
            self.log(line, lv)
        code = stdout.channel.recv_exit_status()
        return code, tail

    # ---------- 产物生成 ----------
    def fill(self, tpl, **kv):
        out = tpl
        for k, v in kv.items():
            out = out.replace("@@%s@@" % k, str(v))
        return out

    def gen_units(self, root, venv):
        files = {}
        for key, sub in SUBJECTS:
            content = self.fill(UNIT_TEMPLATE, SUBJECT=sub, PORT=self.ports[key],
                                USER=self.user, ROOT=root, VENV=venv)
            files["%s-%s.service" % (self.prefix, key)] = content
        return files

    def gen_nginx(self, portal_root):
        loc = []
        for i, (key, _) in enumerate(SUBJECTS):
            port = self.ports[key]
            loc.append("    location = /%s/app { return 301 /%s/app/; }" % (key, key))
            loc.append("    location /%s/ { proxy_pass http://127.0.0.1:%d/; }" % (key, port))
        content = self.fill(NGINX_TEMPLATE, NGINX_PORT=self.nginx_port,
                            DEFAULT_SERVER=self.default_server,
                            PORTAL_ROOT=portal_root,
                            LOCATION_BLOCK="\n".join(loc))
        return content

    def gen_setup_sh(self, root, venv, portal_root):
        keys = [k for k, _ in SUBJECTS]
        units = " ".join("%s-%s" % (self.prefix, k) for k in keys)
        enable = "systemctl enable %s >/dev/null 2>&1 || true" % units
        start = "systemctl restart %s" % units
        ports = " ".join(str(self.ports[k]) for k in keys)
        deep = []
        for key, _ in SUBJECTS:
            deep.append(
                'if curl -sf -m 5 "http://127.0.0.1:%s/%s/app/practice" >/dev/null; then '
                'echo "[OK] SPA 深链接 /%s/app/practice"; '
                'else echo "[FAIL] SPA 深链接 /%s/app/practice"; FAIL=1; fi'
                % (self.nginx_port, key, key, key))
        return self.fill(SETUP_SH, ROOT=root, VENV=venv, USER=self.user,
                         SUDO_U=self.sudo_u, PORTAL_ROOT=portal_root,
                         ENABLE_CMDS=enable, START_CMDS=start, PORTS=ports,
                         NGINX_PORT=self.nginx_port,
                         NGINX_SITE="/etc/nginx/sites-available/" + self.site_name,
                         WRITE_ENV=self.env_shell(root),
                         DEEPLINK_CHECKS="\n".join(deep))

    def gen_cleanup_sh(self, root, portal_root):
        units = " ".join("%s-%s" % (self.prefix, k) for k, _ in SUBJECTS)
        return self.fill(CLEANUP_SH, UNITS=units, PREFIX=self.prefix,
                         SITE_NAME=self.site_name, ROOT=root, PORTAL_ROOT=portal_root)

    # ---------- 主流程 ----------
    def remote_home(self):
        return self.exec_out("echo $HOME").strip() or ("/root" if self.is_root else "/home/" + self.user)

    def plan(self):
        home = self.remote_home()
        if self.test_mode:
            root = home + "/studycenter-test"
            portal_root = "/var/www/studycenter-test"
        else:
            root = home + "/studycenter"
            portal_root = "/var/www/studycenter"
        return root, root + "/venv", portal_root

    def upload_payload(self, remote_dir):
        self.exec_out("mkdir -p " + remote_dir)
        remote_file = remote_dir + "/payload.tar.gz"
        size = os.path.getsize(PAYLOAD_PATH)
        last = [0]

        def cb(sent, total):
            if sent - last[0] >= 2 * 1024 * 1024 or sent == total:
                last[0] = sent
                self.log("  上传进度 %.1f / %.1f MB" % (sent / 1048576, total / 1048576))

        self.log("上传部署包 (%.1f MB) ..." % (size / 1048576))
        self.sftp.put(PAYLOAD_PATH, remote_file, callback=cb)
        self.log("[OK] 部署包上传完成", "ok")

    def write_remote(self, remote, content, mode=None):
        with self.sftp.open(remote, "w") as f:
            f.write(content.encode("utf-8") if isinstance(content, str) else content)
        if mode is not None:
            self.sftp.chmod(remote, mode)

    def run_deploy(self):
        import paramiko  # noqa: F401  (确保打包)
        t0 = time.time()
        try:
            self.connect()
            self.ensure_sudo()
            self.check_os()
            root, venv, portal_root = self.plan()
            self.log("部署目录：%s | 虚拟环境：%s" % (root, venv))
            self.log("Web 访问端口：%d%s" % (self.nginx_port, "" if self.nginx_port == 80 else "（自定义）"))

            # 端口冲突处理：测试模式自动顺延；生产模式提示；单学科时后端端口自动挑空闲
            used = self.used_ports()
            if self.nginx_port in used:
                if self.test_mode:
                    for p in range(self.nginx_port + 1, self.nginx_port + 30):
                        if p not in used:
                            self.nginx_port = p
                            self.log("  [i] 测试端口被占用，改用 %d" % p)
                            break
                else:
                    self.log("  [!] 端口 %d 已被占用，nginx 可能启动失败，可换一个端口重试" % self.nginx_port, "fail")
            if len(SUBJECTS) == 1:
                key = SUBJECTS[0][0]
                self.sudo_out("systemctl stop %s-%s 2>/dev/null || true" % (self.prefix, key))
                free = self.pick_free_port(self.base_port)
                self.ports = {key: free}
                self.log("后端内部端口：%d（自动避开占用）" % free)

            rdir = "/tmp/sc_deploy"
            self.exec_out("rm -rf %s && mkdir -p %s/units" % (rdir, rdir))
            self.upload_payload(rdir)

            self.log("生成部署脚本与配置 ...")
            for name, content in self.gen_units(root, venv).items():
                self.write_remote("%s/units/%s" % (rdir, name), content)
            self.write_remote("%s/nginx-site.conf" % rdir, self.gen_nginx(portal_root))
            self.write_remote("%s/setup.sh" % rdir, self.gen_setup_sh(root, venv, portal_root), mode=0o755)

            self.log("开始部署（apt / pip 阶段耗时最长）...", "step")
            code, tail = self.run_script(rdir + "/setup.sh")

            result = "FAILED"
            for ln in reversed(tail):
                if "RESULT:" in ln:
                    result = ln.split("RESULT:")[1].strip()
                    break
            if code != 0 and result == "FAILED":
                self.log("[FAIL] 部署脚本异常退出（exit=%d），最后输出如下：" % code, "fail")
                for ln in tail[-15:]:
                    self.log("  " + ln)
                STATE["ok"] = False
                return

            host_ip = self.host
            base = "http://%s" % host_ip if self.nginx_port == 80 else "http://%s:%d" % (host_ip, self.nginx_port)
            urls = [base + "/"]
            urls += [base + "/%s/app/" % k for k, _ in SUBJECTS]
            urls.append(base + "/api-platform.html")
            STATE["urls"] = urls

            if result == "SUCCESS":
                self.log("✅ 部署成功！耗时 %.0f 秒" % (time.time() - t0), "ok")
                self.log("—— 访问地址 ——" if self.is_root else "—— 访问地址（请先确保服务器安全组/防火墙已放行 %d 端口）——" % self.nginx_port, "ok")
                for u in urls:
                    self.log("  " + u, "ok")
                self.log("管理员默认账号：admin / admin123（请尽快登录修改密码）")
                if self.ai_key:
                    self.log("AI 已写入各学科 backend/.env：模型 %s（套卷生成 / AI 问答可直接用）" % self.ai_model, "ok")
                    if self.ai_explain:
                        self.log("解析模型：%s" % self.ai_explain)
                else:
                    self.log("未配置 AI：AI 问答与套卷生成不可用，可在 backend/.env 补 AI_API_KEY 后重启")
                STATE["ok"] = True
            else:
                self.log("⚠ 部署完成但有失败项（见上方 [FAIL] 行），请检查后重试", "fail")
                STATE["ok"] = False
        except Exception as e:
            self.log("[FAIL] " + str(e), "fail")
            STATE["ok"] = False
        finally:
            if not self.keep:
                try:
                    self.exec_out("rm -rf /tmp/sc_deploy", timeout=15)
                except Exception:
                    pass
            self.close()
            STATE["running"] = False

    def run_cleanup(self):
        try:
            self.connect()
            self.ensure_sudo()
            root, venv, portal_root = self.plan()
            rdir = "/tmp/sc_deploy"
            self.exec_out("rm -rf %s && mkdir -p %s" % (rdir, rdir))
            self.write_remote("%s/cleanup.sh" % rdir, self.gen_cleanup_sh(root, portal_root), mode=0o755)
            code, tail = self.run_script(rdir + "/cleanup.sh", timeout=120)
            ok = "CLEANUP_DONE" in "\n".join(tail)
            self.log("[OK] 测试部署已清理" if ok else "[FAIL] 清理脚本异常（exit=%d）" % code,
                     "ok" if ok else "fail")
        except Exception as e:
            self.log("[FAIL] " + str(e), "fail")
        finally:
            self.close()


def start_deploy(cfg, test_mode=False, keep=False):
    if STATE["running"]:
        return False, "已有部署正在进行"
    STATE.update({"running": True, "ok": None, "urls": None})
    d = Deployer(cfg, test_mode=test_mode, keep=keep)
    threading.Thread(target=d.run_deploy, daemon=True).start()
    return True, "started"


# ============================================================ 浏览器界面（v2 全新视觉）

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>学习中心 · 一键部署</title>
<style>
:root{
  --bg:#05060a; --ink:#f4f6fb; --sub:#8f9bb3; --dim:#5b6780;
  --line:rgba(255,255,255,.09); --glass:rgba(255,255,255,.035);
  --grad:linear-gradient(135deg,#6366f1 0%,#8b5cf6 45%,#d946ef 100%);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{min-height:100%}
body{
  font-family:"Inter","SF Pro SC","PingFang SC","Microsoft YaHei UI","Microsoft YaHei",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);overflow-x:hidden;-webkit-font-smoothing:antialiased;
}
/* ── 背景层：网格 + 极光 + 光晕跟随 ── */
.bg{position:fixed;inset:0;z-index:-2;pointer-events:none}
.bg::before{content:"";position:absolute;inset:0;
  background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);
  background-size:56px 56px;
  mask-image:radial-gradient(ellipse 80% 55% at 50% 0%,#000 25%,transparent 72%);
  -webkit-mask-image:radial-gradient(ellipse 80% 55% at 50% 0%,#000 25%,transparent 72%)}
.blob{position:fixed;z-index:-3;border-radius:50%;filter:blur(110px);opacity:.22;pointer-events:none}
.blob.a{width:560px;height:560px;left:-140px;top:-180px;background:radial-gradient(circle at 30% 30%,#4f46e5,transparent 65%);animation:drift1 22s ease-in-out infinite alternate}
.blob.b{width:520px;height:520px;right:-160px;top:220px;background:radial-gradient(circle at 70% 40%,#7c3aed,transparent 65%);animation:drift2 26s ease-in-out infinite alternate}
.blob.c{width:440px;height:440px;left:38%;bottom:-230px;background:radial-gradient(circle at 50% 50%,#0891b2,transparent 65%);opacity:.15;animation:drift1 30s ease-in-out infinite alternate-reverse}
@keyframes drift1{from{transform:translate(0,0) scale(1)}to{transform:translate(70px,50px) scale(1.12)}}
@keyframes drift2{from{transform:translate(0,0) scale(1)}to{transform:translate(-60px,-70px) scale(1.15)}}
.cursor-glow{position:fixed;inset:0;z-index:-1;pointer-events:none;
  background:radial-gradient(600px circle at var(--mx,50%) var(--my,18%),rgba(99,102,241,.10),transparent 62%)}

.wrap{max-width:680px;margin:0 auto;padding:56px 20px 48px}

@keyframes fadeUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.rise{opacity:0;animation:fadeUp .7s cubic-bezier(.2,.7,.3,1) forwards}

/* ── Hero ── */
.hero{text-align:center;margin-bottom:36px}
.hero .badge{display:inline-flex;align-items:center;gap:8px;font-size:11px;letter-spacing:2.5px;color:#a5b4fc;
  border:1px solid rgba(129,140,248,.28);background:rgba(99,102,241,.08);padding:7px 14px;border-radius:999px;
  margin-bottom:22px;text-transform:uppercase}
.hero .badge i{width:6px;height:6px;border-radius:50%;background:#818cf8;box-shadow:0 0 10px #818cf8}
.hero h1{font-size:38px;font-weight:800;letter-spacing:-.5px;line-height:1.25;
  background:linear-gradient(180deg,#fff 30%,#c7d2fe 100%);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero p.sub{margin-top:14px;font-size:15px;color:var(--sub);line-height:1.9}
.chips{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:20px}
.chip{font-size:12px;color:#c7d2fe;background:var(--glass);border:1px solid var(--line);
  padding:6px 13px;border-radius:999px;transition:transform .2s,border-color .2s}
.chip:hover{transform:translateY(-2px);border-color:rgba(165,180,252,.4)}

/* ── 卡片 ── */
.card{background:var(--glass);border:1px solid var(--line);border-radius:20px;padding:28px;
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  box-shadow:0 24px 70px -30px rgba(0,0,0,.85);position:relative}
.card::before{content:"";position:absolute;inset:0;border-radius:20px;padding:1px;pointer-events:none;
  background:linear-gradient(135deg,rgba(129,140,248,.4),transparent 28%,transparent 72%,rgba(217,70,239,.32));
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude}

/* ── 表单 ── */
.fgrid{display:grid;grid-template-columns:1fr 132px;gap:14px}
.fgrid .full{grid-column:1/-1}
.hintline{margin-top:9px;font-size:11.5px;color:var(--dim);line-height:1.7}
label{display:block;font-size:11.5px;letter-spacing:1.2px;color:var(--dim);margin-bottom:8px;font-weight:600}
input{width:100%;background:rgba(255,255,255,.045);border:1px solid var(--line);color:var(--ink);
  border-radius:12px;padding:13px 15px;font-size:14.5px;outline:none;transition:border .18s,box-shadow .18s,background .18s}
input::placeholder{color:#4b5670}
input:focus{border-color:#818cf8;background:rgba(255,255,255,.07);box-shadow:0 0 0 4px rgba(99,102,241,.15)}
input.err{border-color:#f87171;animation:shake .35s}@keyframes shake{25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
/* AI 配置区块 */
.ai-sec{padding:16px;border:1px solid rgba(129,140,248,.22);border-radius:14px;
  background:rgba(99,102,241,.05);margin-bottom:4px}
.ai-sec>label{margin-bottom:10px!important}
.ai-row{display:grid;grid-template-columns:1.35fr 1fr;gap:12px;margin-bottom:10px}
.ai-row input{margin-bottom:0!important}
.ai-sec input{margin-bottom:10px}
.ai-sec input:last-of-type{margin-bottom:0}
.req{color:#f87171;font-weight:700;letter-spacing:0}
.chk{display:flex!important;align-items:center;gap:8px;margin-bottom:0!important;
  margin-top:12px;font-size:12px;color:var(--dim);cursor:pointer;letter-spacing:0}
.chk input{width:auto!important;margin:0!important;accent-color:#818cf8}
.ai-sec input:disabled{opacity:.4;cursor:not-allowed}
details.notice{margin-top:18px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.02);font-size:12.5px}
details.notice summary{cursor:pointer;padding:11px 15px;color:var(--sub);font-weight:600;list-style:none;display:flex;align-items:center;gap:8px}
details.notice summary::-webkit-details-marker{display:none}
details.notice summary::before{content:"ⓘ";color:#818cf8;font-size:14px}
details.notice[open] summary{border-bottom:1px solid var(--line)}
details.notice .body{padding:12px 15px;color:var(--sub);line-height:2.1}
details.notice b{color:#c7d2fe;font-weight:600}
.btn-main{width:100%;margin-top:20px;height:52px;border:none;border-radius:14px;cursor:pointer;
  font-size:15.5px;font-weight:700;letter-spacing:6px;color:#fff;font-family:inherit;
  background:var(--grad);background-size:200% 100%;
  box-shadow:0 14px 34px -8px rgba(139,92,246,.55),inset 0 1px 0 rgba(255,255,255,.25);
  transition:transform .18s,box-shadow .18s,background-position .45s;position:relative;overflow:hidden}
.btn-main:hover{transform:translateY(-2px);background-position:100% 0;
  box-shadow:0 20px 44px -10px rgba(139,92,246,.7),inset 0 1px 0 rgba(255,255,255,.25)}
.btn-main:active{transform:translateY(0)}
.btn-main:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn-main::after{content:"";position:absolute;top:0;left:-80%;width:50%;height:100%;
  background:linear-gradient(105deg,transparent,rgba(255,255,255,.35),transparent);
  transform:skewX(-20deg);animation:sweep 4.5s ease-in-out infinite}
@keyframes sweep{0%,60%{left:-80%}100%{left:180%}}

/* ── 部署中 ── */
#prog{display:none}
.steps{display:flex;justify-content:space-between;margin-bottom:28px}
.st{flex:1;display:flex;flex-direction:column;align-items:center;position:relative;min-width:0}
.st .dot{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:700;color:var(--dim);background:rgba(255,255,255,.04);
  border:1px solid var(--line);transition:all .3s;z-index:1}
.st .lb{margin-top:9px;font-size:11px;color:var(--dim);white-space:nowrap;transition:color .3s}
.st:not(:last-child)::after{content:"";position:absolute;top:16px;left:calc(50% + 24px);
  width:calc(100% - 48px);height:2px;background:rgba(255,255,255,.1);transition:background .3s}
.st.done .dot{background:rgba(52,211,153,.14);border-color:rgba(52,211,153,.5);color:#34d399}
.st.done .lb{color:#a7b4c9}
.st.done:not(:last-child)::after{background:linear-gradient(90deg,#34d399,rgba(52,211,153,.15))}
.st.act .dot{background:var(--grad);border-color:transparent;color:#fff;animation:pulse 1.6s infinite}
.st.act .lb{color:#c7d2fe}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(139,92,246,.55)}70%{box-shadow:0 0 0 13px rgba(139,92,246,0)}100%{box-shadow:0 0 0 0 rgba(139,92,246,0)}}
.statusrow{display:flex;align-items:center;gap:14px;margin-bottom:14px}
.pill{font-size:12px;padding:6px 14px;border-radius:999px;color:#c7d2fe;white-space:nowrap;
  background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.3)}
.bar{flex:1;height:6px;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden;position:relative}
.bar i{position:absolute;top:0;bottom:0;width:36%;border-radius:99px;background:var(--grad);animation:run 1.15s ease-in-out infinite}
@keyframes run{0%{left:-36%}100%{left:100%}}
#log{background:rgba(2,4,10,.78);border:1px solid var(--line);border-radius:14px;height:330px;overflow-y:auto;
  padding:16px 18px;font:12px/1.85 "Cascadia Code",Consolas,"JetBrains Mono",monospace;
  white-space:pre-wrap;word-break:break-all}
#log div{animation:ln .25s ease forwards;opacity:0}
@keyframes ln{from{opacity:0;transform:translateY(3px)}to{opacity:1}}
#log .step{color:#7dd3fc;font-weight:700}
#log .ok{color:#34d399}
#log .fail{color:#f87171;font-weight:600}
#log .info{color:#8b96ab}
#log::-webkit-scrollbar{width:8px}
#log::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:99px}
#log::-webkit-scrollbar-track{background:transparent}

/* ── 结果 ── */
#result{display:none;margin-top:18px;text-align:center}
.badge-big{width:84px;height:84px;border-radius:50%;margin:6px auto 18px;display:flex;align-items:center;
  justify-content:center;font-size:38px;animation:pop .6s cubic-bezier(.2,1.6,.4,1)}
#result.good .badge-big{background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.4);box-shadow:0 0 60px rgba(52,211,153,.22)}
#result.bad .badge-big{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.4)}
@keyframes pop{from{transform:scale(.3);opacity:0}to{transform:scale(1);opacity:1}}
#result h2{font-size:22px;font-weight:800}
#result.good h2{color:#6ee7b7}
#result.bad h2{color:#fca5a5}
#result .desc{font-size:13px;color:var(--sub);margin-top:8px;line-height:1.9}
.urls{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:22px 0 6px;text-align:left}
.u{display:flex;align-items:center;gap:10px;padding:12px 14px;border-radius:12px;text-decoration:none;
  background:rgba(255,255,255,.04);border:1px solid var(--line);transition:all .18s;color:#93c5fd}
.u:hover{transform:translateY(-2px);border-color:rgba(147,197,253,.4);background:rgba(59,130,246,.08)}
.u .ic{font-size:17px}
.u .meta{flex:1;min-width:0}
.u .nm{font-size:12px;color:#c7d2fe;margin-bottom:2px}
.u .ad{font-size:11.5px;color:#7d8aa5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:Consolas,monospace}
.mini{display:flex;gap:10px;margin-top:20px}
.mini button{flex:1;height:44px;border-radius:12px;cursor:pointer;font-size:13.5px;font-weight:600;font-family:inherit;
  border:1px solid var(--line);background:rgba(255,255,255,.04);color:#dbe2f0;transition:all .18s}
.mini button:hover{background:rgba(255,255,255,.09)}
.mini button.primary{background:var(--grad);border:none;color:#fff;box-shadow:0 10px 26px -8px rgba(139,92,246,.6)}
.fail-tips{margin:18px 0 4px;text-align:left;font-size:12.5px;color:var(--sub);line-height:2.2}
.fail-tips li{list-style:none;padding-left:22px;position:relative}
.fail-tips li::before{content:"•";position:absolute;left:6px;color:#f87171}
footer{margin-top:34px;text-align:center;font-size:11.5px;color:#414c63;line-height:2}
@media (max-width:560px){
  .fgrid{grid-template-columns:1fr}.urls{grid-template-columns:1fr}.hero h1{font-size:30px}
  .st .lb{display:none}.st:not(:last-child)::after{display:none}
}
</style>
</head>
<body>
<div class="bg"></div>
<div class="blob a"></div><div class="blob b"></div><div class="blob c"></div>
<div class="cursor-glow"></div>

<div class="wrap">
  <section class="hero">
    <div class="badge rise" style="animation-delay:.05s"><i></i>STUDY CENTER DEPLOYER</div>
    <h1 class="rise" style="animation-delay:.15s">学习中心 · 一键部署</h1>
    <p class="sub rise" style="animation-delay:.25s">在一台全新的 Ubuntu 服务器上，自动完成六学科学习系统的完整部署<br>源码 · 题库数据库 · 门户官网 · 开机自启 —— 全程无需手动登录服务器</p>
    <div class="chips rise" style="animation-delay:.35s">
      <span class="chip">🧪 化学</span><span class="chip">📐 数学</span><span class="chip">🧭 物理</span>
      <span class="chip">🧬 生物</span><span class="chip">📖 语文</span><span class="chip">🔤 英语</span>
    </div>
  </section>

  <div class="card rise" id="formCard" style="animation-delay:.45s">
    <div class="fgrid">
      <div><label>服务器 IP</label><input id="host" placeholder="例如 192.168.1.100" spellcheck="false"></div>
      <div><label>SSH 端口</label><input id="sshport" value="22" spellcheck="false"></div>
      <div><label>用户名</label><input id="user" value="root" placeholder="root 或有 sudo 权限的账号" spellcheck="false"></div>
      <div><label>密码</label><input id="pwd" type="password" placeholder="SSH / sudo 密码"></div>
      <div class="full"><label>Web 访问端口</label>
        <input id="webport" value="80" spellcheck="false">
        <div class="hintline">默认 80；若该端口被占用可填 8080、8090 等，部署后的访问地址会自动带上端口</div>
      </div>
      <div class="full ai-sec">
        <label>AI 模型配置 <span class="req">必填</span></label>
        <div class="ai-row">
          <input id="aikey" placeholder="API Key（例如 ark-xxxxxxxx）" spellcheck="false" autocomplete="off">
          <input id="aimodel" value="doubao-seed-2-0-mini-260428" spellcheck="false" placeholder="模型名称">
        </div>
        <input id="aibase" value="https://ark.cn-beijing.volces.com/api/v3" spellcheck="false" placeholder="API 地址">
        <input id="aiexplain" placeholder="解析模型（可选，留空则与上面的模型相同）" spellcheck="false">
        <div class="hintline">部署时直接写进各学科 backend/.env 并生效：套卷生成、AI 问答、错题讲解装完就能用，不用再登录服务器改配置</div>
        <label class="chk"><input type="checkbox" id="noai" onchange="toggleAI()"> 暂不配置 AI（部署后 AI 功能不可用）</label>
      </div>
    </div>
    <details class="notice">
      <summary>部署须知</summary>
      <div class="body">
        · 适用<b>全新 Ubuntu / Debian</b> 服务器（需能联网），部署到 <b>/home/用户名/studycenter</b>，默认占用 <b>80</b> 端口（可自定义）<br>
        · 会<b>覆盖</b>该机已有的 studycenter 部署；云服务器请提前在安全组放行 80 端口<br>
        · 完成后管理员账号 <b>admin / admin123</b>（请尽快修改）；AI 问答需配置 AI_API_KEY
      </div>
    </details>
    <button class="btn-main" id="btn" onclick="startDeploy()">开始部署</button>
  </div>

  <div class="card" id="prog">
    <div class="steps" id="steps"></div>
    <div class="statusrow"><span class="pill" id="pill">正在部署，请稍候…</span><div class="bar"><i></i></div></div>
    <div id="log"></div>
  </div>

  <div class="card" id="result"></div>

  <footer class="rise" style="animation-delay:.55s">内嵌完整部署包：六学科源码 · 前端页面 · 题库数据库 · 门户官网 · 依赖锁定<br>
    v@@VER@@ · 仅支持 Ubuntu / Debian · 建议配置 2 核 4G · 首次部署约 3-6 分钟</footer>
</div>

<script>
const STEPS=['系统依赖','防火墙','解压部署包','虚拟环境','Python 依赖','服务注册','健康检查'];
const ICONS=['🏫','🧪','📐','🧭','🧬','📖','🔤','🛠️'];
const NAMES=['门户官网','化学','数学','物理','生物','语文','英语','API 开放平台'];
let since=0, timer=null, finished=false, STATE_URLS=[];
const $=id=>document.getElementById(id);

function buildSteps(){
  $('steps').innerHTML=STEPS.map((s,i)=>
    '<div class="st" id="st'+i+'"><div class="dot">'+(i+1)+'</div><div class="lb">'+s+'</div></div>').join('');
}
function setStep(n){
  STEPS.forEach((_,i)=>{
    const el=$('st'+i); if(!el)return;
    el.className='st'+(i<n-1?' done':(i===n-1?' act':''));
    const d=el.querySelector('.dot');
    if(i<n-1) d.innerHTML='✓'; else d.textContent=String(i+1);
  });
}
function finishSteps(){
  STEPS.forEach((_,i)=>{
    const el=$('st'+i); if(!el)return;
    el.className='st done'; el.querySelector('.dot').innerHTML='✓';
  });
}
function addLine(ln){
  const box=$('log');
  const d=document.createElement('div');
  d.className=ln.lv; d.textContent=ln.t; box.appendChild(d);
  const m=ln.t.match(/\[步骤 (\d+)\/(\d+)\]/);
  if(m) setStep(+m[1]);
  if(ln.t.indexOf('部署流程结束')>=0) finishSteps();
  box.scrollTop=box.scrollHeight;
}

function toggleAI(){
  const off=$('noai').checked;
  ['aikey','aimodel','aibase','aiexplain'].forEach(id=>{ const e=$(id); if(e) e.disabled=off; });
}

async function startDeploy(){
  const host=$('host').value.trim(), user=$('user').value.trim(), pwd=$('pwd').value;
  const webport=$('webport').value.trim()||'80';
  const noai=$('noai').checked;
  const aikey=$('aikey').value.trim(), aimodel=$('aimodel').value.trim();
  const aibase=$('aibase').value.trim(), aiexplain=$('aiexplain').value.trim();
  let bad=false;
  for(const id of ['host','pwd']){
    const e=$(id); e.classList.remove('err');
    if(!e.value.trim()){ e.classList.add('err'); bad=true; }
  }
  const wpEl=$('webport'); wpEl.classList.remove('err');
  if(!/^\d+$/.test(webport)||+webport<1||+webport>65535){ wpEl.classList.add('err'); bad=true; }
  const keyEl=$('aikey'); keyEl.classList.remove('err');
  if(!noai && !aikey){ keyEl.classList.add('err'); bad=true; }
  if(bad){
    if(!noai && !aikey) alert('请填写 AI API Key（或勾选「暂不配置 AI」）');
    return;
  }
  const btn=$('btn'); btn.disabled=true; btn.textContent='正在启动…';
  try{
    const r=await fetch('/api/deploy',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({host,sshport:$('sshport').value.trim(),user,password:pwd,webport,
        aikey:noai?'':aikey,aimodel,aibase,aiexplain:noai?'':aiexplain,noai})});
    const j=await r.json();
    if(!j.ok){ btn.disabled=false; btn.textContent='开始部署'; alert(j.msg||'启动失败'); return; }
  }catch(e){
    btn.disabled=false; btn.textContent='开始部署'; alert('无法连接本地部署服务'); return;
  }
  $('formCard').style.display='none';
  $('prog').style.display='block';
  $('result').style.display='none';
  finished=false; buildSteps();
  timer=setInterval(poll,600); poll();
}

async function poll(){
  try{
    const r=await fetch('/api/log?since='+since);
    const j=await r.json();
    since=j.total;
    for(const ln of j.lines) addLine(ln);
    if(j.state==='done'&&!finished){
      finished=true; clearInterval(timer);
      showResult(j.ok, j.urls||[]);
    }
  }catch(e){ /* 服务可能正在收尾 */ }
}

function showResult(ok,urls){
  STATE_URLS=urls;
  const el=$('result');
  el.style.display='block';
  el.className='card '+(ok?'good':'bad');
  if(ok){
    el.innerHTML='<div class="badge-big">✅</div><h2>部署成功</h2>'
      +'<div class="desc">整套六学科学习系统已上线，点击卡片即可访问</div>'
      +'<div class="urls">'+urls.map((u,i)=>
          '<a class="u" target="_blank" href="'+u+'"><span class="ic">'+(ICONS[i]||'🔗')+'</span>'
          +'<span class="meta"><div class="nm">'+(NAMES[i]||'')+'</div><div class="ad">'+u+'</div></span></a>').join('')
      +'</div><div class="mini"><button onclick="copyUrls()">复制全部地址</button>'
      +'<button class="primary" onclick="shutdown()">完成并退出</button></div>';
  }else{
    el.innerHTML='<div class="badge-big">⚠️</div><h2>部署失败</h2>'
      +'<div class="desc">请查看日志中的红色 [FAIL] 行定位原因，修复后可直接重新部署（可重复执行）</div>'
      +'<ul class="fail-tips"><li>SSH 密码错误，或该用户没有 sudo 权限</li>'
      +'<li>目标系统不是 Ubuntu / Debian</li>'
      +'<li>服务器无法访问外网（apt / pip 需要联网）</li>'
      +'<li>80 端口被其他程序占用</li></ul>'
      +'<div class="mini"><button onclick="location.reload()">返回重新部署</button>'
      +'<button class="primary" onclick="shutdown()">退出程序</button></div>';
  }
  el.scrollIntoView({behavior:'smooth'});
}

function copyUrls(){
  navigator.clipboard.writeText(STATE_URLS.join('\n')).then(()=>alert('已复制到剪贴板'));
}

async function shutdown(){
  try{ await fetch('/api/shutdown',{method:'POST'}); }catch(e){}
  window.close();
  setTimeout(function(){
    document.body.innerHTML='<div style="display:flex;height:100vh;align-items:center;justify-content:center;color:#8f9bb3;font-size:14px;font-family:system-ui">程序已退出，可直接关闭本页面</div>';
  },300);
}

document.addEventListener('mousemove',function(e){
  document.body.style.setProperty('--mx',e.clientX+'px');
  document.body.style.setProperty('--my',e.clientY+'px');
});

/* 预览调试用（正常部署不会触发） */
window.__mockLog=function(lines){
  $('formCard').style.display='none'; $('prog').style.display='block';
  buildSteps(); lines.forEach(addLine);
};
window.__mock=function(lines,ok,urls){
  $('formCard').style.display='none'; $('prog').style.display='block';
  buildSteps(); lines.forEach(addLine); showResult(ok,urls);
};
buildSteps();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默访问日志
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            body = PAGE_HTML.replace("@@VER@@", VERSION).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/api/log"):
            since = 0
            try:
                since = int(self.path.split("since=")[1].split("&")[0])
            except Exception:
                pass
            snap = LOG.snapshot(since)
            state = "running" if STATE["running"] else "done"
            self._json({"lines": snap["lines"], "total": snap["total"],
                        "state": state, "ok": STATE["ok"], "urls": STATE["urls"]})
        elif self.path == "/api/ping":
            self._json({"ok": True, "version": VERSION})
        else:
            self._json({"err": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            data = {}
        if self.path == "/api/deploy":
            if STATE["running"]:
                self._json({"ok": False, "msg": "已有部署正在进行"})
                return
            cfg = {"host": data.get("host", ""), "ssh_port": data.get("sshport", "22"),
                   "user": data.get("user", "root"), "password": data.get("password", ""),
                   "web_port": data.get("webport", "80"),
                   "ai_key": data.get("aikey", ""),
                   "ai_base": data.get("aibase", ""),
                   "ai_model": data.get("aimodel", ""),
                   "ai_explain_model": data.get("aiexplain", "")}
            if not cfg["host"] or not cfg["password"]:
                self._json({"ok": False, "msg": "请填写服务器 IP 和密码"})
                return
            if not cfg["ai_key"] and not data.get("noai"):
                self._json({"ok": False, "msg": "请填写 AI API Key，或勾选「暂不配置 AI」"})
                return
            ok, msg = start_deploy(cfg)
            self._json({"ok": ok, "msg": msg})
        elif self.path == "/api/shutdown":
            self._json({"ok": True})
            threading.Thread(target=delayed_exit, daemon=True).start()
        else:
            self._json({"err": "not found"}, 404)


def delayed_exit():
    time.sleep(0.4)
    os._exit(0)


def start_server(no_browser=False):
    port = 8765
    httpd = None
    for p in range(8765, 8790):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            port = p
            break
        except OSError:
            continue
    if httpd is None:
        print("无法绑定本地端口 8765-8789")
        sys.exit(1)
    url = "http://127.0.0.1:%d" % port
    print("部署界面: " + url)
    if not no_browser:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


# ============================================================ 命令行模式

def headless(cfg, test_mode, keep, cleanup):
    import logging
    logging.basicConfig(level=logging.CRITICAL)
    try:  # 控制台 GBK 编码下打印 emoji 会崩溃，统一改为 UTF-8 输出
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if cleanup:
        test_mode = True
    d = Deployer(cfg, test_mode=test_mode, keep=keep)
    if cleanup:
        orig = LOG.add

        def tee(text, level="info"):
            print("[log]", text)
            orig(text, level)
        LOG.add = tee
        d.run_cleanup()
        return 0
    orig = LOG.add

    def tee(text, level="info"):
        print("[log]", text)
        orig(text, level)
    LOG.add = tee
    d.run_deploy()
    return 0 if STATE["ok"] else 1


def main():
    args = sys.argv[1:]
    if not PAYLOAD_PATH or not os.path.exists(PAYLOAD_PATH):
        print("错误：缺少内嵌部署包 payload.tar.gz")
        sys.exit(2)

    def get(flag, default=None):
        if flag in args:
            return args[args.index(flag) + 1]
        return default

    headless_mode = "--headless" in args
    test_mode = "--test-mode" in args
    keep = "--keep" in args
    cleanup = "--cleanup" in args

    if headless_mode:
        cfg = {"host": get("--host", ""), "ssh_port": get("--ssh-port", "22"),
               "user": get("--user", "root"), "password": get("--password", ""),
               "web_port": get("--web-port", "")}
        sys.exit(headless(cfg, test_mode, keep, cleanup))

    start_server(no_browser="--no-browser" in args)


if __name__ == "__main__":
    main()
