# -*- coding: utf-8 -*-
"""学习报告 PDF 生成测试"""
import pymupdf

from app.services.report_pdf import build_report_pdf


def test_build_report_pdf():
    stats = {
        "total_questions": 12,
        "correct_count": 8,
        "accuracy": 66.7,
        "avg_time_spent": 52,
        "streak_days": 3,
    }
    trend = [
        {"date": "2026-11-01", "total": 2, "correct": 1, "accuracy": 50},
        {"date": "2026-11-02", "total": 4, "correct": 3, "accuracy": 75},
    ]
    knowledge = {
        "details": [
            {"knowledge_point": "化学平衡", "total_done": 5, "correct_count": 3, "accuracy": 60},
        ],
        "weak_points": ["化学平衡"],
    }
    recent = [{
        "question_title": "测试题目",
        "is_correct": True,
        "score": 4,
        "total_score": 4,
        "submitted_at": "2026-11-15T02:00:00",
    }]
    data = build_report_pdf(
        {"name": "测试同学", "username": "tester"},
        stats, trend, knowledge, {"days": 91, "active_days": 2}, recent,
    )
    assert data.startswith(b"%PDF")
    doc = pymupdf.open(stream=data, filetype="pdf")
    assert doc.page_count == 2
    text = "".join(page.get_text() for page in doc)
    assert "化学学习报告" in text
    assert "化学平衡" in text
    assert "12" in text
    doc.close()
