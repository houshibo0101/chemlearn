"""
题目图片自检脚本
检查内容中提到"图"但images字段为空的题目
用法：
  python check_missing_images.py          # 只列出缺图题目
  python check_missing_images.py --delete # 列出并删除缺图题目
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.models.question import Question
from sqlalchemy import select
import json

# 表示题目需要配图的关键词
IMAGE_KEYWORDS = [
    '如图', '见图', '图所示', '下图', '上图', '图中',
    '装置图', '装置如图', '装置如下',
    '结构图', '结构如图', '结构简式如图',
    '曲线图', '曲线如图', '变化曲线',
    '流程图', '流程如图', '流程如下',
    '晶胞', '晶胞结构',
    '示意图', '示意如图',
    '转化关系如图', '转化关系如下',
    '反应历程', '历程如图',
    '实验装置', '装置图',
    '合成路线', '路线如图', '路线如下',
    '工作原理', '原理如图',
    '滴定曲线', '分布系数',
    '沉淀溶解平衡曲线',
]

def needs_image(content):
    """判断题目内容是否需要配图"""
    if not content:
        return False
    for kw in IMAGE_KEYWORDS:
        if kw in content:
            return True
    return False

def parse_images(images_str):
    """解析images字段"""
    if not images_str:
        return []
    try:
        return json.loads(images_str)
    except:
        return []

async def check_questions(delete=False):
    async with AsyncSessionLocal() as db:
        # 查询所有题目
        result = await db.execute(select(Question).order_by(Question.id))
        questions = result.scalars().all()

        total = len(questions)
        has_image = 0
        missing_image = []
        no_image_needed = 0

        for q in questions:
            images = parse_images(q.images)
            if images:
                has_image += 1
            elif needs_image(q.content):
                missing_image.append(q)
            else:
                no_image_needed += 1

        print(f"{'='*60}")
        print(f"题目图片自检报告")
        print(f"{'='*60}")
        print(f"总题目数: {total}")
        print(f"已有图片: {has_image}")
        print(f"不需要图片: {no_image_needed}")
        print(f"缺图题目: {len(missing_image)}")
        print(f"{'='*60}")

        if missing_image:
            print(f"\n缺图题目列表:")
            print(f"{'-'*60}")
            for q in missing_image:
                # 找出匹配的关键词
                matched = [kw for kw in IMAGE_KEYWORDS if kw in (q.content or '')]
                print(f"ID={q.id:4d} | {q.question_code:20s} | {q.title[:30]:30s} | 关键词: {','.join(matched[:3])}")

            if delete:
                print(f"\n{'='*60}")
                print(f"正在删除 {len(missing_image)} 道缺图题目...")
                ids = [q.id for q in missing_image]
                for q in missing_image:
                    await db.delete(q)
                await db.commit()
                print(f"删除完成！剩余题目: {total - len(missing_image)}")
            else:
                print(f"\n提示: 运行 python check_missing_images.py --delete 可删除以上缺图题目")
        else:
            print(f"\n所有需要配图的题目都有图片，无需处理！")

        return missing_image

if __name__ == "__main__":
    delete = "--delete" in sys.argv
    asyncio.run(check_questions(delete=delete))
