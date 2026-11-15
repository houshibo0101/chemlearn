# -*- coding: utf-8 -*-
"""套卷 PDF 按题号裁剪配图"""
import os

import pymupdf
import pytest

from app.api.papers import _can_review
from app.models import Paper, User, UserRole
from app.services import paper_service as ps


def test_crop_question_images_text_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "PAPER_ROOT", str(tmp_path / "papers"))
    monkeypatch.setattr(ps, "FIGURE_ROOT", str(tmp_path / "papers" / "figures"))

    pid = 12345
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((60, 100), "1. First question with a figure", fontsize=14)
    page.insert_text((60, 300), "2. Second question", fontsize=14)
    page.insert_text((60, 500), "3. Third question", fontsize=14)
    pdf = doc.tobytes()
    ps.save_page_images(pid, [page.get_pixmap(dpi=150).tobytes("png")])

    questions = [
        {"no": 1, "page": 1, "has_figure": True},
        {"no": 2, "page": 1, "has_figure": False},
        {"no": 3, "page": 1, "has_figure": True},
    ]
    count = ps.crop_question_images(pid, pdf, questions)
    assert count == 2
    assert questions[0]["figures"] == ["q1.png"]
    assert questions[2]["figures"] == ["q3.png"]
    assert os.path.isfile(ps.figure_image_path(pid, "q1.png"))
    assert os.path.isfile(ps.figure_image_path(pid, "q3.png"))
    assert not os.path.exists(ps.figure_image_path(pid, "q2.png"))


def test_crop_pdf_region_normalized(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "PAPER_ROOT", str(tmp_path / "papers"))
    monkeypatch.setattr(ps, "FIGURE_ROOT", str(tmp_path / "papers" / "figures"))
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    pdf = doc.tobytes()

    name = ps.crop_pdf_region(pdf, 7, 1, 0.1, 0.1, 0.4, 0.3, "manual_q1_test.png")
    assert name == "manual_q1_test.png"
    path = ps.figure_image_path(7, name)
    assert os.path.isfile(path)
    pix = pymupdf.Pixmap(path)
    assert pix.width > 100 and pix.height > 100
    assert ps.page_count(7) == 0


def test_review_permissions():
    owner = User(id=10, role=UserRole.TEACHER)
    other = User(id=11, role=UserRole.TEACHER)
    admin = User(id=12, role=UserRole.ADMIN)
    paper = Paper(id=1, uploader_id=10)
    assert _can_review(paper, owner) is True
    assert _can_review(paper, other) is False
    assert _can_review(paper, admin) is True

