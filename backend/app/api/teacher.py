"""
老师功能 API - 查看学生错题、班级统计等
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.class_room import ClassRoom, TeacherClass
from app.models.wrong_question import WrongQuestion
from app.models.question import Question

router = APIRouter(prefix="/teacher", tags=["老师功能"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/classes/{class_id}/wrong-questions")
async def get_class_wrong_questions(
    class_id: int,
    student_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """老师查看班级学生错题情况"""
    if current_user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        raise HTTPException(403, "无权限")

    # 验证老师是否管理该班级
    if current_user.role == UserRole.TEACHER:
        tc = (await db.execute(
            select(TeacherClass).where(
                TeacherClass.teacher_id == current_user.id,
                TeacherClass.class_id == class_id,
            )
        )).scalar_one_or_none()
        if not tc:
            raise HTTPException(403, "你不管理该班级")

    # 获取班级学生
    students_query = select(User).where(User.class_id == class_id, User.role == UserRole.STUDENT)
    if student_id:
        students_query = students_query.where(User.id == student_id)
    students = (await db.execute(students_query)).scalars().all()

    result = []
    for student in students:
        wrongs = (await db.execute(
            select(WrongQuestion).where(WrongQuestion.user_id == student.id).order_by(WrongQuestion.last_wrong_at.desc())
        )).scalars().all()

        wrong_list = []
        for w in wrongs:
            q = (await db.execute(select(Question).where(Question.id == w.question_id))).scalar_one_or_none()
            wrong_list.append({
                "id": w.id,
                "question_id": w.question_id,
                "question_code": q.question_code if q else None,
                "title": q.title if q else "题目已删除",
                "wrong_count": w.wrong_count,
                "last_wrong_at": w.last_wrong_at.isoformat() if w.last_wrong_at else None,
            })

        result.append({
            "student_id": student.id,
            "student_name": student.full_name or student.username,
            "wrong_count": len(wrongs),
            "wrong_questions": wrong_list,
        })

    return {"items": result, "total": len(result)}


@router.get("/classes/{class_id}/stats")
async def get_class_stats(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """班级学习统计"""
    if current_user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        raise HTTPException(403, "无权限")

    # 老师只能看自己管理的班级
    if current_user.role == UserRole.TEACHER:
        is_teacher = (await db.execute(
            select(TeacherClass).where(
                TeacherClass.teacher_id == current_user.id,
                TeacherClass.class_id == class_id
            )
        )).scalar_one_or_none()
        if not is_teacher:
            raise HTTPException(403, "你不管理该班级")

    students = (await db.execute(
        select(User).where(User.class_id == class_id, User.role == UserRole.STUDENT)
    )).scalars().all()

    total_wrong = 0
    student_stats = []
    for s in students:
        wrong_count = (await db.execute(
            select(func.count(WrongQuestion.id)).where(WrongQuestion.user_id == s.id)
        )).scalar()
        total_wrong += wrong_count or 0
        student_stats.append({
            "student_id": s.id,
            "name": s.full_name or s.username,
            "wrong_count": wrong_count or 0,
        })

    # 按错题数排序
    student_stats.sort(key=lambda x: x["wrong_count"], reverse=True)

    return {
        "class_id": class_id,
        "student_total": len(students),
        "total_wrong_questions": total_wrong,
        "avg_wrong_per_student": round(total_wrong / len(students), 1) if students else 0,
        "students": student_stats,
    }


@router.get("/my-classes")
async def get_my_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取老师管理的班级"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可访问")

    class_ids = (await db.execute(
        select(TeacherClass.class_id).where(TeacherClass.teacher_id == current_user.id)
    )).scalars().all()

    classes = []
    for cid in class_ids:
        c = (await db.execute(select(ClassRoom).where(ClassRoom.id == cid))).scalar_one_or_none()
        if c:
            student_count = (await db.execute(
                select(func.count(User.id)).where(User.class_id == cid, User.role == UserRole.STUDENT)
            )).scalar()
            classes.append({
                "id": c.id,
                "name": c.name,
                "grade": c.grade,
                "student_count": student_count or 0,
            })

    return {"items": classes, "total": len(classes)}
