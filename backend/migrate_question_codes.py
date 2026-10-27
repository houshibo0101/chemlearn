"""
给已有题目补唯一编号 Q0001, Q0002...
"""
import asyncio
import sys
sys.path.insert(0, '/home/mc/chemlearn/backend')

from app.core.database import AsyncSessionLocal
from app.models import Question
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as db:
        questions = (await db.execute(select(Question).order_by(Question.id.asc()))).scalars().all()
        count = 0
        for i, q in enumerate(questions, 1):
            if not q.question_code:
                q.question_code = f"Q{i:04d}"
                count += 1
        await db.commit()
        print(f"已为 {count} 道题目补编号，共 {len(questions)} 道题")


if __name__ == "__main__":
    asyncio.run(main())
