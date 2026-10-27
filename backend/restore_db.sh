#!/bin/bash
# ChemLearn 数据库恢复脚本
# 用法：./restore_db.sh chemlearn_20260928_120000.db.gz

BACKUP_DIR="/home/mc/chemlearn/backups"
DB_PATH="/home/mc/chemlearn/backend/chemlearn.db"

if [ -z "$1" ]; then
    echo "用法: $0 <备份文件名>"
    echo ""
    echo "可用备份:"
    ls -lh "$BACKUP_DIR"/chemlearn_*.db.gz 2>/dev/null | tail -10
    exit 1
fi

BACKUP_FILE="$BACKUP_DIR/$1"

# 如果用户只给了文件名，自动加.gz后缀
if [ ! -f "$BACKUP_FILE" ] && [ -f "${BACKUP_FILE}.gz" ]; then
    BACKUP_FILE="${BACKUP_FILE}.gz"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "即将恢复备份: $BACKUP_FILE"
echo "目标数据库: $DB_PATH"
echo ""
read -p "确认恢复？这将覆盖当前数据库！(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

# 先备份当前数据库
CURRENT_BACKUP="$BACKUP_DIR/before_restore_$(date +%Y%m%d_%H%M%S).db"
cp "$DB_PATH" "$CURRENT_BACKUP"
gzip -f "$CURRENT_BACKUP"
echo "[INFO] 当前数据库已备份到: ${CURRENT_BACKUP}.gz"

# 停止后端服务
echo "[INFO] 停止后端服务..."
pkill -f uvicorn
sleep 2

# 恢复数据库
gunzip -c "$BACKUP_FILE" > "$DB_PATH"

if [ $? -eq 0 ]; then
    echo "[OK] 数据库恢复成功"
else
    echo "[ERROR] 恢复失败，正在还原..."
    gunzip -c "${CURRENT_BACKUP}.gz" > "$DB_PATH"
    echo "[INFO] 已还原到恢复前状态"
    exit 1
fi

# 重启后端服务
echo "[INFO] 重启后端服务..."
cd /home/mc/chemlearn/backend
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 > backend.log 2>&1 &
sleep 3

# 验证
curl -s -o /dev/null -w "后端状态: HTTP %{http_code}\n" http://127.0.0.1:8000/api/v1/auth/login
echo "[OK] 恢复完成！"
