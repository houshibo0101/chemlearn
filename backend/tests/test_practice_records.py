# -*- coding: utf-8 -*-
"""
做题记录与学习报告闭环测试
链路：注册→登录→提交答案（对/错）→做题记录留痕→统计→趋势→知识点→热力图
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import Question, PracticeRecord
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, username: str) -> dict:
    """注册并登录，返回 {'token':..., 'headers':...}"""
    reg = await client.post("/api/v1/auth/register", json={
        "username": username,
        "password": "test123456",
        "full_name": f"测试_{username}",
        "role": "student",
        "grade": "高一",
    })
    if reg.status_code not in (200, 201):
        # 可能已存在，直接登录
        pass
    login = await client.post("/api/v1/auth/login", json={
        "username": username, "password": "test123456"
    })
    assert login.status_code == 200, f"登录失败: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _make_question(kp: str = "物质的量", qtype: str = "single", answer: str = "A") -> int:
    """直接向测试库插入一道题，返回 id"""
    async with AsyncSessionLocal() as session:
        q = Question(
            question_code=f"TEST-PR-{datetime.now(timezone.utc).timestamp()}",
            title="测试题：1 mol 水含有多少个分子？",
            content="选择题",
            question_type=qtype,
            difficulty="easy",
            grade="高一",
            knowledge_point=kp,
            options='[{"key":"A","text":"6.02e23"},{"key":"B","text":"3.01e23"}]',
            answer=answer,
            analysis="阿伏伽德罗常数",
        )
        session.add(q)
        await session.commit()
        await session.refresh(q)
        return q.id


class TestPracticeRecords:
    """做题记录闭环"""

    async def test_answer_creates_record_and_stats(self, client: AsyncClient):
        """提交答案后：记录留痕、统计正确、错题本联动"""
        headers = await _register_and_login(client, f"pr{datetime.now(timezone.utc).timestamp():.0f}")
        qid = await _make_question(kp="物质的量", answer="A")

        # 1) 答对
        r1 = await client.post("/api/v1/questions/answer", headers=headers, json={
            "question_id": qid, "user_answer": "A", "time_spent": 12, "source": "practice"
        })
        assert r1.status_code == 200, r1.text
        assert r1.json()["is_correct"] is True

        # 2) 再答错一次
        r2 = await client.post("/api/v1/questions/answer", headers=headers, json={
            "question_id": qid, "user_answer": "B", "time_spent": 8, "source": "practice"
        })
        assert r2.status_code == 200
        assert r2.json()["is_correct"] is False

        # 3) 做题历史：2 条，含题目信息
        hist = await client.get("/api/v1/practice-records", headers=headers, params={"page": 1, "page_size": 10})
        assert hist.status_code == 200, hist.text
        body = hist.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        item = body["items"][0]
        assert item["question_title"] and item["knowledge_point"] == "物质的量"
        assert item["time_spent"] in (12, 8)

        # 4) 筛选：只看正确的
        flt = await client.get("/api/v1/practice-records", headers=headers,
                               params={"is_correct": "1"})
        assert flt.json()["total"] == 1
        # "0" 字符串的 truthy 陷阱验证
        flt0 = await client.get("/api/v1/practice-records", headers=headers,
                                params={"is_correct": "0"})
        assert flt0.json()["total"] == 1

        # 5) 统计概览
        stats = await client.get("/api/v1/practice-records/stats", headers=headers)
        s = stats.json()
        assert s["total_questions"] == 2
        assert s["correct_count"] == 1
        assert s["accuracy"] == 50.0
        assert s["avg_time_spent"] == 10
        assert s["streak_days"] >= 1  # 今天做过题
        assert len(s["weekly_trend"]) == 7 and s["weekly_trend"][-1]["total"] >= 2

        # 6) 趋势 / 知识点 / 热力图
        trend = (await client.get("/api/v1/practice-records/trend", headers=headers)).json()
        assert trend["days"] == 14 and len(trend["trend"]) == 14
        assert trend["trend"][-1]["total"] == 2

        kp = (await client.get("/api/v1/practice-records/knowledge", headers=headers)).json()
        assert kp["total_done"] == 2
        assert kp["overall_accuracy"] == 50.0
        assert kp["details"][0]["mastery"] == "薄弱"  # 50% 正确率
        assert kp["details"][0]["knowledge_point"] == "物质的量"

        heat = (await client.get("/api/v1/practice-records/heatmap", headers=headers)).json()
        assert heat["active_days"] >= 1 and len(heat["cells"]) == 91
        assert heat["cells"][-1]["count"] == 2

        # 7) 错题本联动：答错后错题本应有 1 条
        wrongs = await client.get("/api/v1/wrong-questions", headers=headers)
        assert wrongs.status_code == 200
        assert wrongs.json().get("total", 0) >= 1 or len(wrongs.json().get("items", [])) >= 1

    async def test_records_are_user_isolated(self, client: AsyncClient):
        """用户间做题记录隔离"""
        h1 = await _register_and_login(client, f"pru1_{datetime.now(timezone.utc).timestamp():.0f}")
        h2 = await _register_and_login(client, f"pru2_{datetime.now(timezone.utc).timestamp():.0f}")
        qid = await _make_question(kp="氧化还原反应", answer="A")

        await client.post("/api/v1/questions/answer", headers=h1, json={
            "question_id": qid, "user_answer": "A", "source": "practice"
        })
        s2 = (await client.get("/api/v1/practice-records/stats", headers=h2)).json()
        assert s2["total_questions"] == 0  # 用户 2 看不到用户 1 的记录

        s1 = (await client.get("/api/v1/practice-records/stats", headers=h1)).json()
        assert s1["total_questions"] == 1
