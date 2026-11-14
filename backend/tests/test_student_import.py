# -*- coding: utf-8 -*-
"""学生/老师四列 Excel 导入：姓名、学段、班级、身份"""
import io
import time

import pytest
from httpx import AsyncClient
from openpyxl import Workbook, load_workbook

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import User, UserRole, ClassRoom, TeacherClass


async def _make_admin():
    username = "importer%d" % int(time.time() * 1000)
    async with AsyncSessionLocal() as db:
        db.add(User(username=username, hashed_password=hash_password("Test123456"),
                    role=UserRole.ADMIN, is_active=True))
        await db.commit()
    return username


@pytest.mark.asyncio
async def test_import_template_and_four_columns(client: AsyncClient):
    username = await _make_admin()
    login = await client.post("/api/v1/auth/login", json={"username": username, "password": "Test123456"})
    assert login.status_code == 200, login.text
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}

    # 模板四列表头
    r = await client.get("/api/v1/admin/users/import/template", headers=headers)
    assert r.status_code == 200, r.text
    wb = load_workbook(io.BytesIO(r.content))
    ws = wb.active
    assert [c.value for c in ws[1]] == ["姓名", "学段", "班级", "身份"]
    assert "学生" in [c.value for c in ws[2]]
    assert "老师" in [c.value for c in ws[3]]

    suffix = str(int(time.time() * 1000))[-6:]
    class_name = "导入测试班" + suffix
    student_name = "导入学生" + suffix
    teacher_name = "导入老师" + suffix
    default_name = "默认学生" + suffix

    wb = Workbook()
    ws = wb.active
    ws.append(["姓名", "学段", "班级", "身份"])
    ws.append([student_name, "高一", class_name, "学生"])
    ws.append([teacher_name, "高一", class_name, "老师"])
    ws.append([default_name, "高二", "", ""])
    ws.append(["错误身份" + suffix, "高一", class_name, "管理员"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    r = await client.post(
        "/api/v1/admin/users/import",
        headers=headers,
        files={"file": ("students.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["total"] == 4
    assert result["success"] == 3
    assert result["failed"] == 1
    assert any("身份" in d and "无效" in d for d in result["details"])

    async with AsyncSessionLocal() as db:
        cls = (await db.execute(
            ClassRoom.__table__.select().where(ClassRoom.name == class_name)
        )).first()
        assert cls is not None
        class_id = cls.id

        student = (await db.execute(
            User.__table__.select().where(User.full_name == student_name)
        )).first()
        teacher = (await db.execute(
            User.__table__.select().where(User.full_name == teacher_name)
        )).first()
        default = (await db.execute(
            User.__table__.select().where(User.full_name == default_name)
        )).first()
        assert student is not None and student.role == UserRole.STUDENT
        assert student.class_id == class_id
        assert teacher is not None and teacher.role == UserRole.TEACHER
        assert teacher.class_id is None
        assert default is not None and default.role == UserRole.STUDENT

        link = (await db.execute(
            TeacherClass.__table__.select().where(
                TeacherClass.teacher_id == teacher.id,
                TeacherClass.class_id == class_id,
            )
        )).first()
        assert link is not None
