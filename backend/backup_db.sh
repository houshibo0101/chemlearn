#!/bin/bash
# ChemLearn 数据库自动备份脚本
# 每天备份一次，保留最近7天
# 用法：./backup_db.sh

# 配置
BACKUP_DIR="/home/mc/chemlearn/backups"
DB_PATH="/home/mc/chemlearn/backend/chemlearn.db"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 检查数据库文件是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "[ERROR] 数据库文件不存在: $DB_PATH"
    exit 1
fi

# 备份数据库（使用sqlite3的.backup命令，保证一致性）
BACKUP_FILE="$BACKUP_DIR/chemlearn_$DATE.db"
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

if [ $? -eq 0 ]; then
    # 压缩备份文件
    gzip -f "$BACKUP_FILE"
    echo "[OK] 备份成功: ${BACKUP_FILE}.gz"
    echo "     文件大小: $(du -h ${BACKUP_FILE}.gz | cut -f1)"
else
    echo "[ERROR] 备份失败"
    exit 1
fi

# 删除7天前的备份
find "$BACKUP_DIR" -name "chemlearn_*.db.gz" -mtime +$KEEP_DAYS -delete
echo "[INFO] 已清理$KEEP_DAYS天前的旧备份"

# 显示当前备份列表
echo ""
echo "当前备份文件:"
ls -lh "$BACKUP_DIR"/chemlearn_*.db.gz 2>/dev/null | tail -10
