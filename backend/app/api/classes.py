"""
班级管理 API
"""
import random
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.class_room import ClassRoom, TeacherClass

router = APIRouter(prefix="/classes", tags=["班级管理"])


def generate_join_code():
    """生成6位邀请码（大写字母+数字）"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))


class ClassCreate(BaseModel):
    name: str
    grade: Optional[str] = None
    description: Optional[str] = None


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    description: Optional[str] = None


class AssignTeacher(BaseModel):
    teacher_ids: List[int]


class JoinClass(BaseModel):
    join_code: str


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_classes(
    grade: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取班级列表"""
    query = select(ClassRoom)
    if grade:
        query = query.where(ClassRoom.grade == grade)

    # 老师只能看自己的班级
    if current_user.role == UserRole.TEACHER:
        teacher_class_ids = (await db.execute(
            select(TeacherClass.class_id).where(TeacherClass.teacher_id == current_user.id)
        )).scalars().all()
        query = query.where(ClassRoom.id.in_(teacher_class_ids))

    result = await db.execute(query.order_by(ClassRoom.id))
    classes = result.scalars().all()

    # 统计每个班级的学生数
    class_list = []
    for c in classes:
        student_count = (await db.execute(
            select(User).where(User.class_id == c.id, User.role == UserRole.STUDENT)
        )).scalars().all()
        # 只有管理员或该班级老师能看到邀请码
        can_see_code = current_user.role == UserRole.ADMIN
        if not can_see_code and current_user.role == UserRole.TEACHER:
            is_teacher = (await db.execute(
                select(TeacherClass).where(
                    TeacherClass.teacher_id == current_user.id,
                    TeacherClass.class_id == c.id
                )
            )).scalar_one_or_none()
            can_see_code = is_teacher is not None
        class_list.append({
            "id": c.id,
            "name": c.name,
            "grade": c.grade,
            "description": c.description,
            "student_count": len(student_count),
            "join_code": c.join_code if can_see_code else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return {"items": class_list, "total": len(class_list)}


@router.post("")
async def create_class(
    data: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建班级（管理员/老师）"""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(403, "无权限")

    new_class = ClassRoom(
        name=data.name,
        grade=data.grade,
        description=data.description,
        join_code=generate_join_code(),
    )
    db.add(new_class)
    await db.commit()
    await db.refresh(new_class)

    # 如果是老师创建的，自动关联
    if current_user.role == UserRole.TEACHER:
        db.add(TeacherClass(teacher_id=current_user.id, class_id=new_class.id))
        await db.commit()

    return {"id": new_class.id, "name": new_class.name}


@router.put("/{class_id}")
async def update_class(
    class_id: int,
    data: ClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新班级"""
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(403, "无权限")

    c = (await db.execute(select(ClassRoom).where(ClassRoom.id == class_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "班级不存在")

    if data.name:
        c.name = data.name
    if data.grade:
        c.grade = data.grade
    if data.description is not None:
        c.description = data.description
    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{class_id}")
async def delete_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除班级"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "仅管理员可删除")

    c = (await db.execute(select(ClassRoom).where(ClassRoom.id == class_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "班级不存在")

    await db.execute(delete(TeacherClass).where(TeacherClass.class_id == class_id))
    await db.delete(c)
    await db.commit()
    return {"message": "删除成功"}


@router.get("/{class_id}/students")
async def get_class_students(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取班级学生列表"""
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
        select(User).where(User.class_id == class_id, User.role == UserRole.STUDENT).order_by(User.id)
    )).scalars().all()

    return {
        "items": [{
            "id": s.id,
            "username": s.username,
            "full_name": s.full_name,
            "grade": s.grade,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        } for s in students],
        "total": len(students),
    }


@router.post("/{class_id}/teachers")
async def assign_teachers(
    class_id: int,
    data: AssignTeacher,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """给班级分配老师"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "仅管理员可分配老师")

    # 清除旧关联
    await db.execute(delete(TeacherClass).where(TeacherClass.class_id == class_id))

    # 添加新关联
    for tid in data.teacher_ids:
        db.add(TeacherClass(teacher_id=tid, class_id=class_id))
    await db.commit()
    return {"message": "分配成功"}


@router.get("/teachers/all")
async def list_teachers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有老师列表"""
    teachers = (await db.execute(
        select(User).where(User.role == UserRole.TEACHER).order_by(User.id)
    )).scalars().all()
    return {
        "items": [{
            "id": t.id,
            "username": t.username,
            "full_name": t.full_name,
        } for t in teachers],
        "total": len(teachers),
    }


@router.get("/{class_id}/teachers")
async def get_class_teachers(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取班级的老师列表"""
    teacher_ids = (await db.execute(
        select(TeacherClass.teacher_id).where(TeacherClass.class_id == class_id)
    )).scalars().all()

    teachers = (await db.execute(
        select(User).where(User.id.in_(teacher_ids))
    )).scalars().all() if teacher_ids else []

    return {
        "items": [{"id": t.id, "username": t.username, "full_name": t.full_name} for t in teachers],
        "total": len(teachers),
    }


@router.post("/join")
async def join_class(
    data: JoinClass,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """通过邀请码加入班级（老师/学生均可）"""
    if not data.join_code or len(data.join_code.strip()) != 6:
        raise HTTPException(400, "邀请码为6位")

    code = data.join_code.strip().upper()
    c = (await db.execute(
        select(ClassRoom).where(ClassRoom.join_code == code)
    )).scalar_one_or_none()

    if not c:
        raise HTTPException(404, "邀请码无效，班级不存在")

    if current_user.role == UserRole.STUDENT:
        # 学生加入：设置class_id
        if current_user.class_id == c.id:
            raise HTTPException(400, "您已在该班级中")
        current_user.class_id = c.id
        await db.commit()
        return {"message": f"成功加入班级「{c.name}」", "class_id": c.id, "class_name": c.name}
    else:
        # 老师/管理员加入：添加到TeacherClass
        existing = (await db.execute(
            select(TeacherClass).where(
                TeacherClass.teacher_id == current_user.id,
                TeacherClass.class_id == c.id
            )
        )).scalar_one_or_none()

        if existing:
            raise HTTPException(400, "您已加入该班级")

        db.add(TeacherClass(teacher_id=current_user.id, class_id=c.id))
        await db.commit()
        return {"message": f"成功加入班级「{c.name}」", "class_id": c.id, "class_name": c.name}


@router.post("/{class_id}/regenerate-code")
async def regenerate_join_code(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新生成班级邀请码（管理员或班级老师）"""
    c = (await db.execute(select(ClassRoom).where(ClassRoom.id == class_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "班级不存在")

    # 权限检查：管理员或该班级老师
    if current_user.role != UserRole.ADMIN:
        is_teacher = (await db.execute(
            select(TeacherClass).where(
                TeacherClass.teacher_id == current_user.id,
                TeacherClass.class_id == class_id
            )
        )).scalar_one_or_none()
        if not is_teacher:
            raise HTTPException(403, "无权限")

    c.join_code = generate_join_code()
    await db.commit()
    return {"join_code": c.join_code, "message": "邀请码已更新"}
