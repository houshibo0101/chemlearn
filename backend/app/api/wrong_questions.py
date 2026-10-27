"""
错题路由：查看错题、错题AI追问、错题重练、AI变式、导出Excel
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_admin
from app.models import User, WrongQuestion, Question
from app.schemas import WrongQuestionOut, WrongQuestionAIRequest, AIChatResponse, QuestionPracticeOut
from app.services import AIService, ExcelExportService
from app.services.ai_service import AIError
import io
from urllib.parse import quote

router = APIRouter(prefix="/wrong-questions", tags=["错题"])


@router.get("", summary="获取我的错题列表")
async def list_my_wrong_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(WrongQuestion).where(WrongQuestion.user_id == current_user.id)
    count_query = select(func.count(WrongQuestion.id)).where(WrongQuestion.user_id == current_user.id)
    total = (await db.execute(count_query)).scalar()
    query = query.options(joinedload(WrongQuestion.question)).order_by(WrongQuestion.last_wrong_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    result = []
    for wq in items:
        item = WrongQuestionOut.model_validate(wq)
        if wq.question:
            item.question_code = wq.question.question_code or f"Q{wq.question.id:04d}"
            item.question_title = wq.question.title
            item.question_content = wq.question.content
            item.question_type = wq.question.question_type.value if hasattr(wq.question.question_type, 'value') else str(wq.question.question_type)
            item.correct_answer = wq.question.answer
            item.analysis = wq.question.analysis
        result.append(item)
    return {"total": total, "page": page, "page_size": page_size, "items": result}


@router.get("/admin", summary="【管理员】查看所有用户错题")
async def list_all_wrong_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(WrongQuestion)
    count_query = select(func.count(WrongQuestion.id))
    if user_id:
        query = query.where(WrongQuestion.user_id == user_id)
        count_query = count_query.where(WrongQuestion.user_id == user_id)
    total = (await db.execute(count_query)).scalar()
    query = query.options(joinedload(WrongQuestion.user), joinedload(WrongQuestion.question))
    query = query.order_by(WrongQuestion.last_wrong_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    result = []
    for wq in items:
        item = WrongQuestionOut.model_validate(wq)
        if wq.question:
            item.question_code = wq.question.question_code or f"Q{wq.question.id:04d}"
            item.question_title = wq.question.title
            item.question_content = wq.question.content
            item.correct_answer = wq.question.answer
            item.analysis = wq.question.analysis
        result.append(item)
    return {"total": total, "page": page, "page_size": page_size, "items": result}


@router.delete("/{wrong_id}", summary="删除错题记录")
async def delete_wrong_question(
    wrong_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wq = (await db.execute(select(WrongQuestion).where(WrongQuestion.id == wrong_id))).scalar_one_or_none()
    if not wq:
        raise HTTPException(status_code=404, detail="错题记录不存在")
    if wq.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="无权删除他人错题")
    await db.delete(wq)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/ai-explain", response_model=AIChatResponse, summary="错题AI讲解/追问")
async def ai_explain_wrong(
    data: WrongQuestionAIRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wq = (await db.execute(
        select(WrongQuestion).options(joinedload(WrongQuestion.question)).where(
            WrongQuestion.id == data.wrong_question_id,
            WrongQuestion.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not wq:
        raise HTTPException(status_code=404, detail="错题记录不存在")
    if not wq.question:
        raise HTTPException(status_code=404, detail="关联题目不存在")

    reply = await AIService.explain_wrong_question(
        db=db,
        user_id=current_user.id,
        question_title=wq.question.title,
        question_content=wq.question.content,
        correct_answer=wq.question.answer,
        analysis=wq.question.analysis,
        user_answer=wq.user_answer,
        follow_up=data.follow_up,
    )

    # 保存到对话历史（错题讲解也计入用户的1MB配额）
    user_msg = data.follow_up if data.follow_up else f"【错题讲解】{wq.question.title}"
    await AIService.save_message(db, current_user.id, "user", user_msg)
    await AIService.save_message(db, current_user.id, "assistant", reply)
    await AIService.enforce_quota(db, current_user.id)

    from app.core.config import settings
    return AIChatResponse(reply=reply, model=settings.AI_MODEL)


@router.get("/repractice", summary="错题重练：获取错题对应的题目（不含答案，供刷题）")
async def repractice_questions(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按最近错误时间倒序，返回错题对应的完整题目，可直接进入刷题模式"""
    query = (
        select(Question)
        .join(WrongQuestion, WrongQuestion.question_id == Question.id)
        .where(WrongQuestion.user_id == current_user.id)
        .order_by(WrongQuestion.last_wrong_at.desc())
        .limit(limit)
    )
    questions = (await db.execute(query)).scalars().unique().all()
    items = [QuestionPracticeOut.model_validate(q).model_dump(mode="json") for q in questions]
    return {"total": len(items), "items": items}


@router.post("/{wrong_id}/variants", summary="AI生成错题变式题（举一反三）")
async def generate_wrong_variants(
    wrong_id: int,
    count: int = Query(3, ge=1, le=5),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wq = (await db.execute(
        select(WrongQuestion).options(joinedload(WrongQuestion.question)).where(
            WrongQuestion.id == wrong_id,
            WrongQuestion.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not wq:
        raise HTTPException(status_code=404, detail="错题记录不存在")
    if not wq.question:
        raise HTTPException(status_code=404, detail="关联题目不存在")
    q = wq.question

    prompt = f"""请根据下面这道化学题，生成 {count} 道类似的变式题。

原题：
- 题型：{q.question_type.value if hasattr(q.question_type, 'value') else q.question_type}
- 难度：{q.difficulty.value if hasattr(q.difficulty, 'value') else q.difficulty}
- 知识点：{q.knowledge_point or '未标注'}
- 题干：{q.title}
{q.content or ''}
- 选项：{q.options or '无（填空/计算/简答题）'}
- 正确答案：{q.answer}
- 解析：{q.analysis or '无'}

要求：
1. 变式题考察相同知识点，但改变数据、情境或问法，不要和原题一样
2. 难度与原题相当
3. 选择题的 answer 必须是 options 中存在的选项key；填空/计算题 options 给空数组 []
4. 严格只输出 JSON 数组，不要任何其他文字或 markdown 标记

JSON格式：
[{{"title":"题干","question_type":"single","difficulty":"medium","options":[{{"key":"A","text":"..."}}],"answer":"A","analysis":"解析"}}]"""

    try:
        reply, _ = await AIService.chat(prompt)
        content = reply.strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        # 截取最外层 JSON 数组，避免 AI 带前后废话
        start, end = content.find("["), content.rfind("]") + 1
        if start < 0 or end <= start:
            raise HTTPException(status_code=502, detail="AI返回格式异常，请重试")
        raw = json.loads(content[start:end])
        variants = []
        for v in raw if isinstance(raw, list) else []:
            if not isinstance(v, dict) or not v.get("title"):
                continue
            variants.append({
                "title": str(v.get("title"))[:800],
                "question_type": v.get("question_type", "single"),
                "difficulty": v.get("difficulty", "medium"),
                "options": v.get("options") or [],
                "answer": str(v.get("answer", "")),
                "analysis": str(v.get("analysis", "")),
            })
        if not variants:
            raise HTTPException(status_code=502, detail="AI没有生成有效的变式题，请重试")
        return {
            "original": {"id": q.id, "title": q.title, "knowledge_point": q.knowledge_point},
            "count": len(variants),
            "variants": variants,
        }
    except AIError as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)[:300]}")
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI返回内容无法解析，请重试")


@router.get("/export/excel", summary="导出我的错题Excel")
async def export_my_wrong_excel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await ExcelExportService.export_wrong_questions(db, user_id=current_user.id)
    filename = f"wrong_questions_{current_user.username}.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/admin/export/excel", summary="【管理员】导出全部错题Excel")
async def export_all_wrong_excel(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await ExcelExportService.export_wrong_questions(db, user_id=None)
    filename = "all_wrong_questions.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
