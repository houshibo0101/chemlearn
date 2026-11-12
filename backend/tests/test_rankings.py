# -*- coding: utf-8 -*-
"""考试排名：统计、并列名次、权限与 CSV 导出"""
import time
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Exam, ExamStatus, ExamSubmission, User, UserRole

pytestmark = pytest.mark.asyncio

PASSWORD = "test123456"


def _unique(prefix):
    return "%s%d" % (prefix, int(time.time() * 1000000) % 100000000)


async def _make_user(username, role, full_name):
    async with AsyncSessionLocal() as session:
        user = User(username=username, hashed_password=hash_password(PASSWORD),
                    full_name=full_name, role=role, is_active=True)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _login(client, username):
    resp = await client.post("/api/v1/auth/login",
                             json={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": "Bearer " + resp.json()["access_token"]}


async def _make_exam(teacher_id, title="期中化学"):
    async with AsyncSessionLocal() as session:
        exam = Exam(title=title, teacher_id=teacher_id, total_score=100,
                    duration=60, status=ExamStatus.PUBLISHED)
        session.add(exam)
        await session.commit()
        await session.refresh(exam)
        return exam.id


async def _submit(exam_id, student_id, score, started_offset=0, duration=600):
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        session.add(ExamSubmission(
            exam_id=exam_id, student_id=student_id, score=score,
            answers={}, started_at=now - timedelta(seconds=duration + started_offset),
            submitted_at=now - timedelta(seconds=started_offset),
        ))
        await session.commit()


class TestExamRanking:
    async def test_teacher_student_permissions_and_export(self, client: AsyncClient):
        teacher = await _make_user(_unique("rt"), UserRole.TEACHER, "排名老师")
        other_teacher = await _make_user(_unique("ro"), UserRole.TEACHER, "别的老师")
        s1 = await _make_user(_unique("ra"), UserRole.STUDENT, "高分学生")
        s2 = await _make_user(_unique("rb"), UserRole.STUDENT, "中等学生")
        s3 = await _make_user(_unique("rc"), UserRole.STUDENT, "未考学生")
        th = await _login(client, teacher.username)
        oh = await _login(client, other_teacher.username)
        h1 = await _login(client, s1.username)
        h2 = await _login(client, s2.username)
        h3 = await _login(client, s3.username)

        exam_id = await _make_exam(teacher.id, "期末考试")
        await _submit(exam_id, s1.id, 90, started_offset=0, duration=500)
        await _submit(exam_id, s2.id, 80, started_offset=10, duration=600)
        await _submit(exam_id, s3.id, 80, started_offset=20, duration=700)
        # s3 也提交了，只是用于名次；另建一个未提交的学生
        s4 = await _make_user(_unique("rd"), UserRole.STUDENT, "没参加学生")
        h4 = await _login(client, s4.username)

        # 老师视角：完整排名
        resp = await client.get("/api/v1/rankings/exam/%d" % exam_id, headers=th)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["exam_title"] == "期末考试"
        assert data["participant_count"] == 3
        assert data["max_score"] == 90
        assert data["min_score"] == 80
        assert data["score_distribution"] == {"0-59": 0, "60-69": 0, "70-79": 0,
                                              "80-89": 2, "90-100": 1}
        assert len(data["ranking"]) == 3
        assert data["ranking"][0]["student_name"] == "高分学生"
        assert data["ranking"][0]["rank"] == 1
        assert data["ranking"][1]["rank"] == 2
        assert data["ranking"][2]["rank"] == 2  # 并列

        # 学生视角：只看自己
        mine = await client.get("/api/v1/rankings/exam/%d" % exam_id, headers=h1)
        assert mine.status_code == 200
        assert mine.json()["my_rank"] == 1
        assert mine.json()["my_score"] == 90
        assert mine.json()["ranking"] == []

        second = await client.get("/api/v1/rankings/exam/%d" % exam_id, headers=h2)
        assert second.json()["my_rank"] == 2

        # 没参加的学生：403
        denied = await client.get("/api/v1/rankings/exam/%d" % exam_id, headers=h4)
        assert denied.status_code == 403

        # 非创建老师：403
        other = await client.get("/api/v1/rankings/exam/%d" % exam_id, headers=oh)
        assert other.status_code == 403

        # 导出 CSV（带 BOM）
        export = await client.get("/api/v1/rankings/exam/%d/export" % exam_id, headers=th)
        assert export.status_code == 200
        assert "text/csv" in export.headers["content-type"]
        text = export.content.decode("utf-8-sig")
        assert "高分学生" in text and "中等学生" in text
        assert "排名" in text.splitlines()[0]
        denied_export = await client.get("/api/v1/rankings/exam/%d/export" % exam_id, headers=h1)
        assert denied_export.status_code == 403

        # 管理员也能看
        admin = await _make_user(_unique("adm"), UserRole.ADMIN, "管理员")
        ah = await _login(client, admin.username)
        admin_resp = await client.get("/api/v1/rankings/exam/%d" % exam_id, headers=ah)
        assert admin_resp.status_code == 200
        assert len(admin_resp.json()["ranking"]) == 3

    async def test_missing_exam_404(self, client: AsyncClient):
        user = await _make_user(_unique("rx"), UserRole.TEACHER, "老师")
        headers = await _login(client, user.username)
        resp = await client.get("/api/v1/rankings/exam/99999999", headers=headers)
        assert resp.status_code == 404
