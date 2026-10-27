"""
API 开放平台 - 全部功能开放接口
低风险：question/wrong/ai（用户创建Key时可选）
高风险：class/assignment/exam/admin（需管理员在账户管理中授权）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.models import (
    User, Question, WrongQuestion,
    ClassRoom, TeacherClass,
    Assignment, AssignmentClass, AssignmentSubmission,
    Exam, ExamClass, ExamQuestion, ExamSubmission,
)
from app.api.open_platform import verify_api_key

router = APIRouter(prefix="/open/v2", tags=["API开放平台-全部功能"])


# ========== 题目相关（scope: question，低风险） ==========

@router.get("/questions", summary="【开放】获取题目列表")
async def open_questions(
    page: int = 1,
    page_size: int = 10,
    grade: Optional[str] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    user: User = Depends(verify_api_key("question")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Question)
    if grade:
        query = query.where(Question.grade == grade)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    if question_type:
        query = query.where(Question.question_type == question_type)
    if knowledge_point:
        query = query.where(Question.knowledge_point.like(f"%{knowledge_point}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    questions = (await db.execute(
        query.order_by(Question.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": q.id,
                "question_code": q.question_code,
                "title": q.title,
                "content": q.content,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "grade": q.grade,
                "knowledge_point": q.knowledge_point,
                "options": q.options,
            }
            for q in questions
        ],
    }


@router.get("/questions/{question_id}", summary="【开放】获取题目详情（含答案解析）")
async def open_question_detail(
    question_id: int,
    user: User = Depends(verify_api_key("question")),
    db: AsyncSession = Depends(get_db),
):
    q = (await db.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {
        "id": q.id,
        "question_code": q.question_code,
        "title": q.title,
        "content": q.content,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "grade": q.grade,
        "knowledge_point": q.knowledge_point,
        "options": q.options,
        "answer": q.answer,
        "analysis": q.analysis,
    }


@router.get("/questions/stats", summary="【开放】题库统计")
async def open_question_stats(
    user: User = Depends(verify_api_key("question")),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count(Question.id)))).scalar()
    by_grade = (await db.execute(
        select(Question.grade, func.count(Question.id)).group_by(Question.grade)
    )).all()
    by_difficulty = (await db.execute(
        select(Question.difficulty, func.count(Question.id)).group_by(Question.difficulty)
    )).all()
    return {
        "total_questions": total,
        "by_grade": [{"grade": g, "count": c} for g, c in by_grade if g],
        "by_difficulty": [{"difficulty": d, "count": c} for d, c in by_difficulty if d],
    }


# ========== 错题本相关（scope: wrong，低风险，只能操作自己的错题） ==========

@router.get("/wrong-questions", summary="【开放】获取错题列表")
async def open_wrong_list(
    page: int = 1,
    page_size: int = 10,
    user: User = Depends(verify_api_key("wrong")),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(
        select(func.count(WrongQuestion.id)).where(WrongQuestion.user_id == user.id)
    )).scalar()
    wrongs = (await db.execute(
        select(WrongQuestion).where(WrongQuestion.user_id == user.id)
        .order_by(WrongQuestion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    items = []
    for w in wrongs:
        q = (await db.execute(select(Question).where(Question.id == w.question_id))).scalar_one_or_none()
        items.append({
            "id": w.id,
            "question_id": w.question_id,
            "question_title": q.title if q else None,
            "wrong_answer": w.wrong_answer,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/wrong-questions", summary="【开放】添加错题")
async def open_add_wrong(
    request: Request,
    user: User = Depends(verify_api_key("wrong")),
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    question_id = body.get("question_id")
    wrong_answer = body.get("wrong_answer", "")
    if not question_id:
        raise HTTPException(status_code=400, detail="question_id必填")
    q = (await db.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    wq = WrongQuestion(user_id=user.id, question_id=question_id, wrong_answer=wrong_answer)
    db.add(wq)
    await db.commit()
    return {"message": "添加成功", "id": wq.id}


@router.delete("/wrong-questions/{wrong_id}", summary="【开放】删除错题")
async def open_delete_wrong(
    wrong_id: int,
    user: User = Depends(verify_api_key("wrong")),
    db: AsyncSession = Depends(get_db),
):
    wq = (await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == wrong_id, WrongQuestion.user_id == user.id)
    )).scalar_one_or_none()
    if not wq:
        raise HTTPException(status_code=404, detail="错题不存在")
    await db.delete(wq)
    await db.commit()
    return {"message": "删除成功"}


# ========== AI问答（scope: ai，低风险） ==========

@router.post("/ai/chat", summary="【开放】AI问答")
async def open_ai_chat(
    request: Request,
    user: User = Depends(verify_api_key("ai")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_service import ai_service
    body = await request.json()
    message = body.get("message", "")
    conversation_id = body.get("conversation_id")
    if not message:
        raise HTTPException(status_code=400, detail="message必填")
    try:
        result = await ai_service.chat(message=message, user_id=user.id, conversation_id=conversation_id)
        return {
            "answer": result.get("answer", ""),
            "conversation_id": result.get("conversation_id"),
            "usage": result.get("usage"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务异常: {e}")


# ========== 班级管理（scope: class，高风险，需管理员授权） ==========

@router.get("/classes", summary="【开放】班级列表（高风险）")
async def open_classes(
    user: User = Depends(verify_api_key("class")),
    db: AsyncSession = Depends(get_db),
):
    classes = (await db.execute(select(ClassRoom).order_by(ClassRoom.id.desc()))).scalars().all()
    return {"items": [{
        "id": c.id, "name": c.name, "grade": c.grade,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in classes]}


@router.get("/classes/{class_id}/students", summary="【开放】班级学生列表（高风险）")
async def open_class_students(
    class_id: int,
    user: User = Depends(verify_api_key("class")),
    db: AsyncSession = Depends(get_db),
):
    students = (await db.execute(
        select(User).where(User.class_id == class_id, User.role == "student")
    )).scalars().all()
    return {"items": [{
        "id": s.id, "username": s.username, "full_name": s.full_name, "grade": s.grade
    } for s in students]}


@router.post("/classes", summary="【开放】创建班级（高风险）")
async def open_create_class(
    request: Request,
    user: User = Depends(verify_api_key("class")),
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    name = body.get("name")
    grade = body.get("grade")
    description = body.get("description", "")
    if not name:
        raise HTTPException(status_code=400, detail="name必填")
    classroom = ClassRoom(name=name, grade=grade, description=description)
    db.add(classroom)
    await db.commit()
    # 关联老师
    tc = TeacherClass(teacher_id=user.id, class_id=classroom.id)
    db.add(tc)
    await db.commit()
    return {"message": "创建成功", "id": classroom.id}


# ========== 作业管理（scope: assignment，高风险） ==========

@router.get("/assignments", summary="【开放】作业列表（高风险）")
async def open_assignments(
    class_id: Optional[int] = None,
    user: User = Depends(verify_api_key("assignment")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Assignment)
    if class_id:
        # 通过AssignmentClass关联
        ac_ids = (await db.execute(
            select(AssignmentClass.assignment_id).where(AssignmentClass.class_id == class_id)
        )).scalars().all()
        query = query.where(Assignment.id.in_(ac_ids))
    assignments = (await db.execute(query.order_by(Assignment.created_at.desc()))).scalars().all()
    return {"items": [{
        "id": a.id, "title": a.title, "description": a.description,
        "teacher_id": a.teacher_id, "question_ids": a.question_ids,
        "start_time": a.start_time.isoformat() if a.start_time else None,
        "end_time": a.end_time.isoformat() if a.end_time else None,
        "status": a.status.value if hasattr(a.status, 'value') else a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in assignments]}


@router.post("/assignments", summary="【开放】创建作业（高风险）")
async def open_create_assignment(
    request: Request,
    user: User = Depends(verify_api_key("assignment")),
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    title = body.get("title")
    class_id = body.get("class_id")
    question_ids = body.get("question_ids", [])
    end_time = body.get("end_time")
    if not title or not class_id:
        raise HTTPException(status_code=400, detail="title和class_id必填")
    assignment = Assignment(
        title=title,
        teacher_id=user.id,
        question_ids=question_ids,
        end_time=end_time,
        status="published",
    )
    db.add(assignment)
    await db.commit()
    # 关联班级
    ac = AssignmentClass(assignment_id=assignment.id, class_id=class_id)
    db.add(ac)
    await db.commit()
    return {"message": "创建成功", "id": assignment.id}


@router.get("/assignments/{assignment_id}/submissions", summary="【开放】作业提交列表（高风险）")
async def open_assignment_submissions(
    assignment_id: int,
    user: User = Depends(verify_api_key("assignment")),
    db: AsyncSession = Depends(get_db),
):
    submissions = (await db.execute(
        select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id)
    )).scalars().all()
    return {"items": [{
        "id": s.id, "student_id": s.student_id, "answers": s.answers,
        "score": s.score, "total_score": s.total_score,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
    } for s in submissions]}


# ========== 考试管理（scope: exam，高风险） ==========

@router.get("/exams", summary="【开放】考试列表（高风险）")
async def open_exams(
    class_id: Optional[int] = None,
    user: User = Depends(verify_api_key("exam")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Exam)
    if class_id:
        ec_ids = (await db.execute(
            select(ExamClass.exam_id).where(ExamClass.class_id == class_id)
        )).scalars().all()
        query = query.where(Exam.id.in_(ec_ids))
    exams = (await db.execute(query.order_by(Exam.created_at.desc()))).scalars().all()
    return {"items": [{
        "id": e.id, "title": e.title, "description": e.description,
        "teacher_id": e.teacher_id, "duration": e.duration,
        "total_score": e.total_score,
        "start_time": e.start_time.isoformat() if e.start_time else None,
        "end_time": e.end_time.isoformat() if e.end_time else None,
        "status": e.status.value if hasattr(e.status, 'value') else e.status,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    } for e in exams]}


@router.post("/exams", summary="【开放】创建考试（高风险）")
async def open_create_exam(
    request: Request,
    user: User = Depends(verify_api_key("exam")),
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    title = body.get("title")
    class_id = body.get("class_id")
    question_ids = body.get("question_ids", [])
    duration = body.get("duration", 60)
    end_time = body.get("end_time")
    if not title or not class_id:
        raise HTTPException(status_code=400, detail="title和class_id必填")
    exam = Exam(
        title=title,
        teacher_id=user.id,
        duration=duration,
        end_time=end_time,
        status="published",
    )
    db.add(exam)
    await db.commit()
    # 关联班级
    ec = ExamClass(exam_id=exam.id, class_id=class_id)
    db.add(ec)
    await db.commit()
    # 关联题目
    for i, qid in enumerate(question_ids):
        eq = ExamQuestion(exam_id=exam.id, question_id=qid, order=i)
        db.add(eq)
    await db.commit()
    return {"message": "创建成功", "id": exam.id}


@router.get("/exams/{exam_id}/submissions", summary="【开放】考试提交列表（高风险）")
async def open_exam_submissions(
    exam_id: int,
    user: User = Depends(verify_api_key("exam")),
    db: AsyncSession = Depends(get_db),
):
    submissions = (await db.execute(
        select(ExamSubmission).where(ExamSubmission.exam_id == exam_id)
    )).scalars().all()
    return {"items": [{
        "id": s.id, "student_id": s.student_id, "answers": s.answers,
        "score": s.score,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
    } for s in submissions]}


# ========== 用户信息（scope: question或ai或wrong都可以访问自己的信息） ==========

@router.get("/user/info", summary="【开放】获取当前用户信息")
async def open_user_info(
    user: User = Depends(verify_api_key("question")),
    db: AsyncSession = Depends(get_db),
):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "grade": user.grade,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
        "allowed_api_scopes": user.allowed_api_scopes,
    }
