# 常见问题

---

## 登录相关

### 忘记管理员密码

```bash
cd backend
python -c "
import sqlite3
from passlib.context import CryptContext
pwd = CryptContext(schemes=['bcrypt']).hash('新密码')
c = sqlite3.connect('chemlearn.db')
c.execute('update users set password_hash=? where username=?', (pwd, 'admin'))
c.commit(); print('已重置')
"
```

或者用环境变量 `ADMIN_PASSWORD` 启动一次，会自动重置 admin 密码。

### 提示「账号已被禁用」

管理员在「账号管理」里把该账号禁用了，取消勾选即可。

### 提示「登录失败次数过多」

防爆破机制：连续输错 5 次会锁一段时间，提示里带剩余秒数。等一会儿或重启服务立刻解锁。

---

## AI 相关

### 提示「AI 服务未配置」

`backend/.env` 里没有 `AI_API_KEY`，或者服务没读到（改完要重启）。详见 [AI 配置](AI-Setup)。

### 提示「账号欠费 AccountOverdueError」

火山引擎账号余额不足，所有模型调用都会 403。充值后恢复。

### AI 生成套卷很慢

正常。8 页扫描版约 4 分钟（OCR 1 分钟 + 结构化 3 分钟）。文字型 PDF 约 2 分钟。

### 生成的题数比卷面少

AI 漏题，长材料（尤其阅读、完形）容易整段跳过。三种处理：

1. 点「重新生成」，模型有随机性，换个结果
2. 用「校对答案」补题
3. 上传时把试卷拆成小份（每次 5 页以内）

---

## 功能相关

### 打开「我的收藏」报 not found

旧版本前端有收藏页但后端没实现接口。升级到最新代码即可（已补齐 `favorites` 模块）。

### 做题页倒计时不准 / 停表

旧版本用递减计数器，浏览器会把后台标签定时器节流到每分钟 1 次。升级到最新版（服务端计时 + 绝对时间重算）。

### 导出的 Excel 打不开

Excel 里题型是中文（单选 / 多选 / 填空…），如果导出的是旧版可能缺题型。升级后端。

### 上传 PDF 提示「没有读到文字」

- 扫描版没有文字层 → 新版会自动走视觉识别（需要多模态模型）
- 如果还是失败，检查是否超过 40 页，或把 PDF 转成 TXT

### 上传大文件失败（502 / 413）

nginx 的 `client_max_body_size` 太小。改成 50m 并 reload：

```bash
sudo sed -i 's/client_max_body_size.*/client_max_body_size 50m;/' /etc/nginx/sites-available/studycenter.conf
sudo nginx -t && sudo systemctl reload nginx
```

---

## 部署相关

### 部署后访问是 404 或看到别的页面

80 端口可能被别的站点占用。检查：

```bash
sudo nginx -T | grep -E "listen|server_name"
ls /etc/nginx/sites-enabled/
```

本项目的配置是 `studycenter.conf`，默认监听 80。想换端口改 `listen`。

### 服务起不来

```bash
sudo systemctl status study-chem
sudo journalctl -u study-chem -n 50 --no-pager
```

常见原因：

| 日志 | 原因 |
|---|---|
| `ModuleNotFoundError` | venv 依赖没装全，重跑 `pip install -r requirements.txt` |
| `Address already in use` | 端口被占，换端口 |
| `默认 SECRET_KEY / admin123` 拦截 | `.env` 里写了 `DEBUG=false`，删掉这行（本项目不需要） |
| `no such table` | 数据库没建，首次启动会自动建，检查文件权限 |

### 前端改了没生效

没 `npm run build`，或者只替换了源码没替换 `dist/app`。后端是 `StaticFiles` 现读磁盘，替换目录即生效，不用重启。

---

## 数据相关

### 数据存在哪

`backend/chemlearn.db`（SQLite 单文件）。备份就是拷这个文件。

### 怎么迁移到新服务器

```bash
# 旧机器
tar czf sc-data.tgz backend/chemlearn.db backend/uploads

# 新机器（部署完成后）
tar xzf sc-data.tgz -C ~/studycenter/化学/
sudo systemctl restart study-chem
```

### 题库是空的

题库不内置在源码里，需要单独下载导入，见 [快速开始](Quick-Start#导入题库)。

### 学生上传的试卷一直「待审核」

需要管理员在「套卷练习」页面点「通过」。审核通过后会自动开始生成做题页。

---

## 性能

### 多人同时用会不会卡

单机 SQLite 支撑几十人同时在线没问题。瓶颈通常在大模型调用（每次几秒到几分钟），不在数据库。

如果要支撑上百人，建议：

- 换 PostgreSQL（改 `DATABASE_URL`）
- AI 调用加队列，避免并发打爆上游

### 数据库越来越大

主要是 `uploads/papers/pages/` 里的页面图（每页约 600KB）。定期清理不再使用的试卷：

```bash
# 删掉 30 天前的试卷页面图
find backend/uploads/papers/pages -type f -mtime +30 -delete
```
