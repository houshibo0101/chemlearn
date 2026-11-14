# -*- coding: utf-8 -*-
"""AI 无关提问计数、5 次停用、老师解封"""
import time

import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import User, UserRole, ClassRoom, TeacherClass, AIRestriction


async def _login(client, username, password="Test123456"):
    r = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.mark.asyncio
async def test_ai_offtopic_ban_and_teacher_unban(client: AsyncClient):
    suffix = str(int(time.time() * 1000))
    async with AsyncSessionLocal() as db:
        student = User(username="aistu" + suffix, hashed_password=hash_password("Test123456"),
                       full_name="测试学生", role=UserRole.STUDENT, is_active=True)
        teacher = User(username="aitea" + suffix, hashed_password=hash_password("Test123456"),
                       full_name="测试老师", role=UserRole.TEACHER, is_active=True)
        db.add_all([student, teacher])
        await db.flush()
        cls = ClassRoom(name="AI测试班" + suffix, grade="高一")
        db.add(cls)
        await db.flush()
        student.class_id = cls.id
        db.add(TeacherClass(teacher_id=teacher.id, class_id=cls.id))
        await db.commit()
        student_id, class_id = student.id, cls.id

    student_h = await _login(client, "aistu" + suffix)
    teacher_h = await _login(client, "aitea" + suffix)

    # 前 4 次：拒绝回答，但不封禁
    for i in range(4):
        r = await client.post("/api/v1/ai/chat", headers=student_h, json={"message": "给我讲个笑话"})
        assert r.status_code == 200, r.text
        assert "无关" in r.json()["reply"]
        assert "已停用" not in r.json()["reply"]
    async with AsyncSessionLocal() as db:
        restriction = (await db.get(AIRestriction, student_id))
        assert restriction.offtopic_count == 4
        assert restriction.banned is False

    # 第 5 次：停用
    r = await client.post("/api/v1/ai/chat", headers=student_h, json={"message": "给我讲个笑话"})
    assert r.status_code == 200
    assert "已停用" in r.json()["reply"]

    # 停用后再次请求 403
    r = await client.post("/api/v1/ai/chat", headers=student_h, json={"message": "继续讲笑话"})
    assert r.status_code == 403
    assert "老师解封" in r.json()["detail"]

    # 老师班级列表能看到停用状态
    r = await client.get("/api/v1/classes/%d/students" % class_id, headers=teacher_h)
    assert r.status_code == 200
    row = next(x for x in r.json()["items"] if x["id"] == student_id)
    assert row["ai_banned"] is True
    assert row["ai_offtopic_count"] == 5

    # 老师解封
    r = await client.post(
        "/api/v1/classes/%d/students/%d/ai-unban" % (class_id, student_id),
        headers=teacher_h,
    )
    assert r.status_code == 200, r.text
    async with AsyncSessionLocal() as db:
        restriction = (await db.get(AIRestriction, student_id))
        assert restriction.banned is False
        assert restriction.offtopic_count == 0

    # 解封后可以继续用（无关问题仍然只拒绝、不回答，但不会直接 403）
    r = await client.post("/api/v1/ai/chat", headers=student_h, json={"message": "给我讲个笑话"})
    assert r.status_code == 200
    assert "无关" in r.json()["reply"]
