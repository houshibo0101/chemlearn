# -*- coding: utf-8 -*-
"""化学连连看：创建、权限、作答、排行榜、批量导入"""
import time

import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import User, UserRole

pytestmark = pytest.mark.asyncio

PASSWORD = "test123456"


async def _make_user(username: str, role: UserRole, full_name: str):
    async with AsyncSessionLocal() as session:
        user = User(
            username=username,
            hashed_password=hash_password(PASSWORD),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _login(client: AsyncClient, username: str) -> dict:
    resp = await client.post("/api/v1/auth/login",
                             json={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": "Bearer " + resp.json()["access_token"]}


def _unique(prefix: str) -> str:
    return "%s%d" % (prefix, int(time.time() * 1000) % 100000000)


SAMPLE_PAIRS = [
    {"left_text": "氢氧化钠", "right_text": "烧碱、火碱", "hint": "NaOH，强碱"},
    {"left_text": "碳酸钠", "right_text": "纯碱、苏打"},
    {"left_text": "氧化钙", "right_text": "生石灰"},
]


class TestMatching:
    async def test_teacher_create_update_and_scope(self, client: AsyncClient):
        teacher = await _make_user(_unique("mt"), UserRole.TEACHER, "连老师")
        other = await _make_user(_unique("mo"), UserRole.TEACHER, "别的老师")
        th = await _login(client, teacher.username)
        oh = await _login(client, other.username)

        created = await client.post("/api/v1/matching/sets", headers=th, json={
            "title": "测试关卡", "category": "common_name", "difficulty": "easy",
            "pairs": SAMPLE_PAIRS,
        })
        assert created.status_code == 201, created.text
        set_id = created.json()["id"]

        manage = await client.get("/api/v1/matching/manage/sets", headers=th)
        assert manage.status_code == 200
        assert manage.json()["total"] == 1
        assert manage.json()["items"][0]["pair_count"] == 3

        # 另一位老师看不到，也改不了
        other_manage = await client.get("/api/v1/matching/manage/sets", headers=oh)
        assert other_manage.json()["total"] == 0
        forbidden = await client.put("/api/v1/matching/sets/%d" % set_id, headers=oh, json={
            "title": "越权修改", "pairs": SAMPLE_PAIRS,
        })
        assert forbidden.status_code == 403

        updated = await client.put("/api/v1/matching/sets/%d" % set_id, headers=th, json={
            "title": "测试关卡（改）", "category": "substance", "difficulty": "medium",
            "is_active": False,
            "pairs": SAMPLE_PAIRS[:2],
        })
        assert updated.status_code == 200, updated.text

        detail = await client.get("/api/v1/matching/sets/%d" % set_id, headers=th)
        assert detail.status_code == 200
        assert detail.json()["pair_count"] == 2
        assert detail.json()["can_edit"] is True

        # 停用后学生看不到
        student = await _make_user(_unique("ms"), UserRole.STUDENT, "连同学")
        sh = await _login(client, student.username)
        student_detail = await client.get("/api/v1/matching/sets/%d" % set_id, headers=sh)
        assert student_detail.status_code == 404

    async def test_student_play_submit_and_leaderboard(self, client: AsyncClient):
        student = await _make_user(_unique("mp"), UserRole.STUDENT, "玩同学")
        author = await _make_user(_unique("ma"), UserRole.TEACHER, "出题老师")
        th = await _login(client, author.username)
        sh = await _login(client, student.username)

        created = await client.post("/api/v1/matching/sets", headers=th, json={
            "title": "学生党关卡", "category": "functional_group", "pairs": SAMPLE_PAIRS,
        })
        set_id = created.json()["id"]

        listing = await client.get("/api/v1/matching/sets", headers=sh)
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1
        assert any(item["id"] == set_id for item in listing.json()["items"])

        detail = await client.get("/api/v1/matching/sets/%d" % set_id, headers=sh)
        assert detail.status_code == 200
        assert len(detail.json()["pairs"]) == 3
        assert detail.json()["can_edit"] is False

        # 学生不能建/管
        denied = await client.post("/api/v1/matching/sets", headers=sh, json={
            "title": "学生不该能建", "pairs": SAMPLE_PAIRS,
        })
        assert denied.status_code == 403
        denied_manage = await client.get("/api/v1/matching/manage/sets", headers=sh)
        assert denied_manage.status_code == 403

        # 配对数量对不上时拒绝提交（防止关卡更新后旧页面刷分）
        bad = await client.post("/api/v1/matching/sets/%d/records" % set_id, headers=sh, json={
            "score": 30, "mistakes": 0, "pairs_total": 2,
            "max_combo": 2, "duration_seconds": 20,
        })
        assert bad.status_code == 400

        submitted = await client.post("/api/v1/matching/sets/%d/records" % set_id, headers=sh, json={
            "score": 42, "mistakes": 1, "pairs_total": 3,
            "max_combo": 3, "duration_seconds": 25,
        })
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["saved"] is True

        summary = await client.get("/api/v1/matching/my/summary", headers=sh)
        assert summary.json()["plays"] == 1
        assert summary.json()["best_score"] == 42

        board = await client.get("/api/v1/matching/sets/%d/leaderboard" % set_id, headers=sh)
        assert board.status_code == 200
        assert board.json()["items"][0]["score"] == 42
        assert board.json()["items"][0]["is_me"] is True

        records = await client.get("/api/v1/matching/manage/sets/%d/records" % set_id, headers=th)
        assert records.status_code == 200
        assert records.json()["total"] == 1
        assert records.json()["items"][0]["username"] == student.username

    async def test_import_csv_and_template(self, client: AsyncClient):
        teacher = await _make_user(_unique("mi"), UserRole.TEACHER, "导入老师")
        th = await _login(client, teacher.username)

        csv_data = "左项,右项,提示\n钠,Na,金属钠\n氯气,Cl₂,黄绿色气体\n".encode("utf-8")
        imported = await client.post(
            "/api/v1/matching/import", headers=th,
            files={"file": ("demo.csv", csv_data, "text/csv")},
            data={"title": "CSV 关卡", "category": "substance", "difficulty": "easy"},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["pair_count"] == 2

        set_id = imported.json()["id"]
        detail = await client.get("/api/v1/matching/sets/%d" % set_id, headers=th)
        assert {p["left_text"] for p in detail.json()["pairs"]} == {"钠", "氯气"}

        template = await client.get("/api/v1/matching/import/template", headers=th)
        assert template.status_code == 200
        assert "spreadsheetml" in template.headers["content-type"]

        # 只有一对有效内容时拒绝
        bad = await client.post(
            "/api/v1/matching/import", headers=th,
            files={"file": ("bad.csv", "左项,右项\n钠,Na\n".encode("utf-8"), "text/csv")},
            data={},
        )
        assert bad.status_code == 400

        deleted = await client.delete("/api/v1/matching/sets/%d" % set_id, headers=th)
        assert deleted.status_code == 200

    async def test_pairs_validation(self, client: AsyncClient):
        teacher = await _make_user(_unique("mv"), UserRole.TEACHER, "校验老师")
        th = await _login(client, teacher.username)

        duplicate_left = await client.post("/api/v1/matching/sets", headers=th, json={
            "title": "重复左项", "pairs": [
                {"left_text": "A", "right_text": "1"},
                {"left_text": "A", "right_text": "2"},
            ],
        })
        assert duplicate_left.status_code == 422

        same_side = await client.post("/api/v1/matching/sets", headers=th, json={
            "title": "左右相同", "pairs": [
                {"left_text": "A", "right_text": "A"},
                {"left_text": "B", "right_text": "C"},
            ],
        })
        assert same_side.status_code == 422

        too_few = await client.post("/api/v1/matching/sets", headers=th, json={
            "title": "只有一对", "pairs": [{"left_text": "A", "right_text": "B"}],
        })
        assert too_few.status_code == 422
