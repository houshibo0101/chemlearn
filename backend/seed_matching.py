# -*- coding: utf-8 -*-
"""给「化学连连看」灌入示例关卡（可重复执行，按标题去重）

用法（在 backend 目录下）：
    python seed_matching.py            # 只补缺失的示例关卡
    python seed_matching.py --force    # 删掉同名关卡（含作答记录）后重建

新装/升级时后端启动会自动灌一次（仅当 matching_sets 表刚创建），
一般不需要手动运行本脚本。
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal, init_db  # noqa: E402
from app.models import User  # noqa: E402
from app.services.matching_seed import seed_matching  # noqa: E402


async def main(force: bool = False):
    await init_db()
    async with AsyncSessionLocal() as db:
        admin = (await db.execute(
            select(User).where(User.username == "admin")
        )).scalar_one_or_none()
        if not admin:
            print("找不到 admin 账号，请先启动一次后端让管理员初始化")
            return 1
        created = await seed_matching(db, admin.id, force=force)
        print("完成，本次新增 %d 套关卡" % created)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="删除同名旧关卡后重建")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(force=args.force)))
