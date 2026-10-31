# 部署指南

---

## 服务器要求

| 项 | 最低 | 建议 |
|---|---|---|
| 系统 | Ubuntu 20.04 / Debian 11 | Ubuntu 22.04 / 24.04 |
| CPU / 内存 | 1 核 2G | 2 核 4G |
| 磁盘 | 10G | 20G+（含试卷和页面图） |
| 网络 | 能访问 apt / pypi / 大模型 API | 同 |

> 需要 `apt` 包管理器和 `systemd`。CentOS / Alpine 不支持自动部署。

---

## 目录结构（部署后）

```
/home/<用户>/studycenter/
├── venv/                    Python 虚拟环境（共用）
├── 化学/
│   ├── backend/             后端代码
│   │   ├── chemlearn.db     数据库（备份就拷这个）
│   │   ├── .env             AI 配置
│   │   └── uploads/         上传的试卷、渲染的页面图
│   └── web/dist/app/        前端构建产物
├── 数学/ 物理/ 生物/ 语文/ 英语/   同结构
└── portal/                  门户页
```

---

## 端口分配

| 服务 | 端口 |
|---|---|
| nginx | 80（可自定义） |
| 化学 | 8000 |
| 数学 | 8001 |
| 物理 | 8002 |
| 生物 | 8003 |
| 语文 | 8004 |
| 英语 | 8005 |

nginx 按前缀转发：

```nginx
location /chem/ { proxy_pass http://127.0.0.1:8000/; }
location /math/ { proxy_pass http://127.0.0.1:8001/; }
...
```

前端 base 是 `/{学科}/app/`，API 是 `/{学科}/api/v1`。

---

## systemd 服务

每个学科一个：

```ini
[Unit]
Description=StudyCenter - 化学 (port 8000)
After=network.target

[Service]
User=<部署用户>
WorkingDirectory=/home/<用户>/studycenter/化学/backend
ExecStart=/home/<用户>/studycenter/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

常用命令：

```bash
sudo systemctl status study-chem     # 状态
sudo systemctl restart study-chem    # 重启
sudo journalctl -u study-chem -f     # 看实时日志
```

---

## 手动部署（不用部署器）

```bash
# 1. 系统依赖
sudo apt update
sudo apt install -y nginx python3-venv python3-pip curl

# 2. 放代码
mkdir -p ~/studycenter/化学
# 把 backend/ 和 web/dist/app/ 拷进去

# 3. 虚拟环境
python3 -m venv ~/studycenter/venv
~/studycenter/venv/bin/pip install -r backend/requirements.txt \
  -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 配置
cat > backend/.env <<'EOF'
AI_API_KEY=ark-xxx
AI_API_BASE=https://ark.cn-beijing.volces.com/api/v3
AI_MODEL=doubao-seed-2-0-mini-260428
AI_TIMEOUT=180
EOF
chmod 600 backend/.env

# 5. 启动
~/studycenter/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 6. 配 systemd + nginx（见上）
```

---

## 升级

代码变了之后：

```bash
# 后端：换个文件重启即可
scp app/services/paper_service.py user@host:~/studycenter/化学/backend/app/services/
sudo systemctl restart study-chem

# 前端：整个 dist/app 替换（后端是 StaticFiles 现读磁盘，不用重启）
scp -r web/dist/app user@host:~/studycenter/化学/web/dist/
```

> 改前端源码后必须 `npm run build`，否则线上还是旧页面。

---

## 数据备份

整个系统就一个 SQLite 文件：

```bash
# 备份
cp ~/studycenter/化学/backend/chemlearn.db ~/backup-$(date +%F).db

# 恢复
cp ~/backup-2026-10-31.db ~/studycenter/化学/backend/chemlearn.db
sudo systemctl restart study-chem
```

试卷和页面图在 `backend/uploads/`，一起备份。

建议加个每日定时：

```bash
# crontab -e
0 3 * * * cp ~/studycenter/化学/backend/chemlearn.db ~/backups/db-$(date +\%F).db
```

---

## 反向代理 / 域名

想挂域名或加 HTTPS，在前面再套一层 nginx 或 Caddy：

```nginx
server {
    listen 443 ssl http2;
    server_name chem.example.com;

    ssl_certificate     /etc/letsencrypt/live/chem.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chem.example.com/privkey.pem;

    client_max_body_size 50m;   # 试卷上传

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_read_timeout 300s;   # AI 生成慢，别卡在 60s
    }
}
```

> `client_max_body_size` 和 `proxy_read_timeout` 这两个一定要调，否则大 PDF 上传失败、生成超时断开。

---

## 部署器参数

命令行用法：

```bash
deployer.py --host 1.2.3.4 --user root --password xxx --web-port 8080
deployer.py --test-mode      # 部署到独立目录和端口，不影响现有服务
deployer.py --cleanup        # 清理测试部署
deployer.py --no-browser     # 只起界面服务，不开浏览器
```

`--test-mode` 会把服务装在 `studycenter-test` 目录、用 9000+ 端口，适合在已有环境上验证。
