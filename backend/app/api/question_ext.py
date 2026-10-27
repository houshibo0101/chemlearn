"""
题目图片上传 + 简答题批改
"""
import os
import json
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.question import Question
from app.core.config import settings
import httpx

router = APIRouter(prefix="/questions", tags=["题目扩展"])

UPLOAD_DIR = "/var/www/chemlearn/uploads/questions"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-image", summary="上传题目图片")
async def upload_question_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传题目图片，返回访问URL"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {"url": f"/uploads/questions/{filename}", "filename": filename}


@router.post("/{question_id}/grade-subjective", summary="批改简答题")
async def grade_subjective(
    question_id: int,
    user_answer: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    简答题批改：先关键词匹配，命中率低于60%则调AI复批
    """
    question = (await db.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    keywords = []
    if question.keywords:
        try:
            keywords = json.loads(question.keywords)
        except:
            pass

    # 关键词匹配
    total_score = sum(kw.get("score", 1) for kw in keywords) if keywords else 10
    got_score = 0
    hit_keywords = []
    for kw in keywords:
        word = kw.get("word", "")
        score = kw.get("score", 1)
        if word and word in user_answer:
            got_score += score
            hit_keywords.append(word)

    hit_rate = got_score / total_score if total_score > 0 else 0
    result = {
        "question_id": question_id,
        "user_answer": user_answer,
        "keyword_score": got_score,
        "total_score": total_score,
        "hit_rate": round(hit_rate, 2),
        "hit_keywords": hit_keywords,
        "method": "keyword",
        "ai_comment": None,
        "final_score": got_score,
    }

    # 命中率低于60%，调AI复批
    if hit_rate < 0.6 and question.answer:
        try:
            ai_result = await _ai_grade(question, user_answer, total_score)
            if ai_result:
                result["method"] = "ai"
                result["ai_comment"] = ai_result.get("comment")
                result["final_score"] = ai_result.get("score", got_score)
        except Exception as e:
            # AI失败则用关键词结果
            pass

    return result


async def _ai_grade(question: Question, user_answer: str, total_score: int) -> dict:
    """调用AI批改简答题"""
    ai_url = getattr(settings, "AI_SERVICE_URL", "http://127.0.0.1:8001")
    prompt = f"""你是化学老师，请批改学生的简答题答案。

题目：{question.title}
{question.content or ''}

参考答案：{question.answer}

学生答案：{user_answer}

请按JSON格式返回：
{{"score": 得分(0-{total_score}), "comment": "评语，指出对在哪里错在哪里"}}

只返回JSON，不要其他内容。"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{ai_url}/v1/chat/completions", json={
            "model": "deepseek-v4-flash-260425",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        })
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # 提取JSON
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    return None
