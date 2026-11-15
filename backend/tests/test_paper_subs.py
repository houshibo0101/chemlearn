# -*- coding: utf-8 -*-
"""套卷填空多小问判分"""
import pytest

from app.models import Paper
from app.services import paper_service as ps


def test_fill_question_drops_stale_options():
    q = ps.normalize_question({
        "no": 1,
        "type": "fill",
        "title": "填空题",
        "options": [{"key": "A", "text": "甲"}, {"key": "B", "text": "乙"}],
    }, 1)
    assert q is not None
    assert q["options"] == []


@pytest.mark.asyncio
async def test_judge_sub_questions_partial(monkeypatch):
    async def no_ai(paper, answers):
        return {}
    monkeypatch.setattr(ps, "ai_grade_subjective", no_ai)

    paper = Paper(
        id=1,
        title="测试卷",
        total_score=3,
        questions_json=[{
            "no": 1,
            "type": "fill",
            "title": "填写下列空白",
            "options": [],
            "score": 3,
            "answer": "2；3；4",
            "analysis": "",
            "sub_questions": [
                {"id": 1, "content": "(1) 2", "answer": "2", "score": 1},
                {"id": 2, "content": "(2) 3", "answer": "3", "score": 1},
                {"id": 3, "content": "(3) 4", "answer": "4", "score": 1},
            ],
        }],
    )
    result = await ps.judge(paper, {"1": {"0": "2", "1": "错误", "2": ""}}, {})
    detail = result["details"][0]
    assert result["score"] == 1
    assert detail["earned"] == 1
    assert len(detail["sub_results"]) == 3
    assert [s["ok"] for s in detail["sub_results"]] == [True, False, False]

    result = await ps.judge(paper, {"1": {"0": "2", "1": "3", "2": "4"}}, {})
    assert result["score"] == 3
    assert result["details"][0]["ok"] is True


@pytest.mark.asyncio
async def test_judge_nested_sub_questions(monkeypatch):
    async def no_ai(paper, answers):
        return {}
    monkeypatch.setattr(ps, "ai_grade_subjective", no_ai)

    paper = Paper(
        id=2,
        title="嵌套小问",
        total_score=4,
        questions_json=[{
            "no": 1,
            "type": "subjective",
            "title": "大题",
            "options": [],
            "score": 4,
            "answer": "2；3",
            "analysis": "",
            "sub_questions": [{
                "id": 1,
                "content": "(1) 第一问",
                "answer": "",
                "score": 3,
                "children": [
                    {"id": 1, "content": "① 第一空", "answer": "2", "score": 1, "children": []},
                    {"id": 2, "content": "② 第二空", "answer": "3", "score": 2, "children": []},
                ],
            }],
        }],
    )
    result = await ps.judge(paper, {"1": {"0.0": "2", "0.1": "3"}}, {})
    assert result["score"] == 3
    detail = result["details"][0]
    assert [s["path"] for s in detail["sub_results"]] == ["0.0", "0.1"]
    assert [s["earned"] for s in detail["sub_results"]] == [1, 2]

