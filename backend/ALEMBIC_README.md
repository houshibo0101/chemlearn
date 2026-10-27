# Alembic 数据库迁移使用说明

## 首次使用（服务器上执行）

```bash
cd ~/chemlearn/backend

# 安装alembic
venv/bin/pip install alembic

# 标记当前数据库为初始版本（数据库已存在，不需要执行迁移）
venv/bin/alembic stamp head

# 执行迁移（给api_keys表加新字段）
venv/bin/alembic upgrade head
```

## 日常使用

### 查看当前版本
```bash
venv/bin/alembic current
```

### 查看历史
```bash
venv/bin/alembic history
```

### 生成新迁移（修改模型后）
```bash
# 自动生成迁移脚本（需要对比模型和数据库）
venv/bin/alembic revision --autogenerate -m "描述修改内容"

# 检查生成的脚本，确认无误后执行
venv/bin/alembic upgrade head
```

### 回滚迁移
```bash
# 回滚一个版本
venv/bin/alembic downgrade -1

# 回滚到指定版本
venv/bin/alembic downgrade 0001_initial
```

## 注意事项

1. SQLite不支持直接删除/修改列，Alembic会自动使用batch模式
2. 每次修改模型后，先生成迁移脚本，检查后再执行
3. 生产环境执行迁移前先备份数据库
4. 迁移脚本会提交到git，团队协作时需要同步
