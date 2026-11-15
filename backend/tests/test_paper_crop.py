# -*- coding: utf-8 -*-
"""套卷 PDF 按题号裁剪配图"""
import os

import pymupdf
import pytest

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
