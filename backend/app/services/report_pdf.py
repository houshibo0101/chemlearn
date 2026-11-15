# -*- coding: utf-8 -*-
"""学习报告 PDF 生成（PyMuPDF，服务端直接输出文件）。

中文使用 PyMuPDF 内置 china-ss，英文/数字使用 helv，避免 CJK 字体把
ASCII 字符渲染成全角宽字符导致排版松散。
"""
from datetime import datetime, timedelta, timezone

import pymupdf

PAGE_W, PAGE_H = 595, 842
M = 44
CJK = "china-ss"
LATIN = "helv"
INK = (0.12, 0.16, 0.24)
MUTED = (0.42, 0.47, 0.56)
BRAND = (0.31, 0.27, 0.90)
LIGHT = (0.96, 0.97, 1.0)
LINE = (0.88, 0.90, 0.94)
GREEN = (0.05, 0.65, 0.45)
RED = (0.86, 0.25, 0.30)
AMBER = (0.95, 0.62, 0.13)


def _char_font(ch: str) -> str:
    return LATIN if ord(ch) < 128 else CJK


def _char_width(ch: str, size: float) -> float:
    if ord(ch) >= 128:
        return size
    if ch in " .,:;'|":
        return size * 0.28
    if ch in "1":
        return size * 0.42
    return size * 0.53


def _text_width(text: str, size: float) -> float:
    return sum(_char_width(ch, size) for ch in str(text or ""))


def _draw(page, x, y, text, size=10, color=INK):
    """逐字符按中/英字体绘制，返回结束 x。"""
    text = str(text or "")
    if not text:
        return x
    run = ""
    font = None
    for ch in text:
        f = _char_font(ch)
        if font is None:
            font = f
        if f != font:
            page.insert_text((x, y), run, fontname=font, fontsize=size, color=color)
            x += _text_width(run, size)
            run = ""
            font = f
        run += ch
    if run:
        page.insert_text((x, y), run, fontname=font, fontsize=size, color=color)
        x += _text_width(run, size)
    return x


def _draw_fit(page, x, y, text, max_width, size=10, color=INK, min_size=6):
    text = str(text or "")
    while size > min_size and _text_width(text, size) > max_width:
        size -= 0.5
    return _draw(page, x, y, text, size, color)


def _wrap_lines(text, max_width, size):
    lines = []
    for paragraph in str(text or "").split("\n"):
        current = ""
        for ch in paragraph:
            if _text_width(current + ch, size) <= max_width:
                current += ch
            else:
                if current:
                    lines.append(current)
                current = ch
        lines.append(current)
    return lines or [""]


def _clip(value, limit=26) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _fmt_time(seconds) -> str:
    try:
        seconds = int(seconds or 0)
    except (TypeError, ValueError):
        seconds = 0
    if seconds < 60:
        return f"{seconds}秒"
    return f"{seconds // 60}分{seconds % 60}秒"


def _local_time(value) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value[:16].replace("T", " ")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return (value + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def _header(page, name, username, subtitle, height=94):
    page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, height), color=None, fill=(0.055, 0.08, 0.15), width=0)
    _draw(page, M, 44, "化学学习报告", 22, (1, 1, 1))
    _draw(page, M, 68, f"{name} · {username} · 生成于 {subtitle}", 9, (0.72, 0.77, 0.88))
    _draw(page, PAGE_W - M - 76, 42, "ChemLearn", 12, (0.78, 0.82, 0.96))
    page.draw_rect(
        pymupdf.Rect(PAGE_W - M - 78, 50, PAGE_W - M, 54),
        color=None, fill=BRAND, width=0,
    )


def _footer(page, index, total):
    page.draw_line(
        pymupdf.Point(M, PAGE_H - 32), pymupdf.Point(PAGE_W - M, PAGE_H - 32),
        color=LINE, width=0.7,
    )
    _draw(page, M, PAGE_H - 18, "ChemLearn · 学习报告", 7.5, MUTED)
    _draw(page, PAGE_W - M - 24, PAGE_H - 18, f"{index} / {total}", 7.5, MUTED)


def _section(page, y, title, note=""):
    page.draw_rect(pymupdf.Rect(M, y - 9, M + 3, y + 3), color=None, fill=BRAND, width=0)
    _draw(page, M + 10, y, title, 12, INK)
    if note:
        _draw(page, M + 10 + _text_width(title, 12) + 10, y, note, 7.5, MUTED)
    page.draw_line(
        pymupdf.Point(M, y + 10), pymupdf.Point(PAGE_W - M, y + 10),
        color=LINE, width=0.7,
    )
    return y + 22


def _summary_cards(page, y, stats):
    cards = [
        ("累计做题（题）", f"{stats.get('total_questions', 0)}", BRAND),
        ("总体正确率", f"{stats.get('accuracy', 0)}%", GREEN),
        ("连续学习（天）", f"{stats.get('streak_days', 0)}", AMBER),
        ("平均用时", _fmt_time(stats.get("avg_time_spent")), (0.2, 0.55, 0.85)),
    ]
    gap = 8
    width = (PAGE_W - 2 * M - gap * 3) / 4
    for i, (label, value, color) in enumerate(cards):
        x = M + i * (width + gap)
        page.draw_rect(
            pymupdf.Rect(x, y, x + width, y + 66),
            color=LINE, fill=LIGHT, width=0.7,
        )
        _draw_fit(page, x + 10, y + 20, label, width - 20, 8, MUTED)
        _draw_fit(page, x + 10, y + 46, value, width - 20, 19, color)
    return y + 82


def _trend_chart(page, y, trend):
    page.draw_rect(
        pymupdf.Rect(M, y, PAGE_W - M, y + 158),
        color=LINE, fill=(0.995, 0.995, 1), width=0.7,
    )
    x0, x1 = M + 30, PAGE_W - M - 28
    top, bottom = y + 16, y + 134
    max_total = max([1] + [int(d.get("total") or 0) for d in trend])
    if not trend:
        _draw(page, x0, y + 80, "暂无趋势数据", 10, MUTED)
        return
    for pct in (0, 50, 100):
        gy = bottom - (bottom - top) * pct / 100
        page.draw_line(pymupdf.Point(x0, gy), pymupdf.Point(x1, gy), color=LINE, width=0.5)
        _draw(page, x1 + 5, gy + 3, f"{pct}%", 6.5, MUTED)
    _draw(page, M + 5, y + 12, "做题量", 6.5, BRAND)
    step = (x1 - x0) / max(len(trend) - 1, 1)
    bar_w = min(13, step * 0.55)
    points = []
    for i, d in enumerate(trend):
        cx = x0 + i * step
        total = int(d.get("total") or 0)
        bh = (bottom - top) * total / max_total if max_total else 0
        if bh > 0:
            page.draw_rect(
                pymupdf.Rect(cx - bar_w / 2, bottom - bh, cx + bar_w / 2, bottom),
                color=None, fill=(0.58, 0.54, 0.96), width=0,
            )
        acc = max(0.0, min(100.0, float(d.get("accuracy") or 0)))
        cy = bottom - (bottom - top) * acc / 100
        points.append((cx, cy))
        if i % max(1, len(trend) // 7) == 0 or i == len(trend) - 1:
            _draw(page, cx - 12, bottom + 13, str(d.get("date", ""))[5:], 6.2, MUTED)
    if len(points) > 1:
        page.draw_polyline(points, color=GREEN, width=1.1)
        for cx, cy in points:
            page.draw_circle(
                pymupdf.Point(cx, cy), 1.8, color=GREEN, fill=(1, 1, 1), width=0.7,
            )
    _draw(page, x1 - 72, y + 12, "正确率", 6.5, GREEN)


def _knowledge_rows(page, y, details):
    if not details:
        _draw(page, M, y + 8, "暂无知识点做题数据", 9, MUTED)
        return y + 24
    for item in details[:8]:
        name = _clip(item.get("knowledge_point") or "未标注", 20)
        acc = max(0.0, min(100.0, float(item.get("accuracy") or 0)))
        _draw(page, M, y + 10, name, 8.5, INK)
        _draw(page, M + 198, y + 10, f"{item.get('total_done', 0)} 题", 7, MUTED)
        bar_x, bar_w = M + 238, 190
        page.draw_rect(
            pymupdf.Rect(bar_x, y + 2, bar_x + bar_w, y + 7),
            color=None, fill=(0.91, 0.92, 0.96), width=0,
        )
        fill_w = bar_w * acc / 100
        color = GREEN if acc >= 80 else AMBER if acc >= 60 else RED
        if fill_w > 0:
            page.draw_rect(
                pymupdf.Rect(bar_x, y + 2, bar_x + fill_w, y + 7),
                color=None, fill=color, width=0,
            )
        _draw(page, bar_x + bar_w + 8, y + 10, f"{acc:.0f}%", 8, color)
        page.draw_line(
            pymupdf.Point(M, y + 18), pymupdf.Point(PAGE_W - M, y + 18),
            color=(0.95, 0.96, 0.98), width=0.5,
        )
        y += 24
    return y


def _recent_rows(page, y, recent):
    if not recent:
        _draw(page, M, y + 8, "还没有做题记录，完成一次练习后这里会出现记录。", 9, MUTED)
        return y + 30
    for item in recent[:8]:
        title = _clip(item.get("question_title") or item.get("title") or "题目", 32)
        ok = item.get("is_correct")
        score = item.get("score")
        total = item.get("total_score")
        result = "正确" if ok else "错误" if ok is False else "待自评"
        color = GREEN if ok else RED if ok is False else MUTED
        _draw(page, M, y + 10, _local_time(item.get("submitted_at")), 7, MUTED)
        _draw(page, M + 105, y + 10, title, 8.2, INK)
        score_text = f"{score}/{total}" if score is not None and total else "—"
        _draw(page, PAGE_W - M - 92, y + 10, score_text, 7.5, MUTED)
        _draw(page, PAGE_W - M - 34, y + 10, result, 7.5, color)
        page.draw_line(
            pymupdf.Point(M, y + 18), pymupdf.Point(PAGE_W - M, y + 18),
            color=(0.95, 0.96, 0.98), width=0.5,
        )
        y += 24
    return y


def _suggestion(knowledge, stats):
    weak = knowledge.get("weak_points") or []
    total = int(stats.get("total_questions") or 0)
    if total == 0:
        return "还没有做题数据。建议先完成 10 道基础题，系统会根据正确率和知识点生成更具体的学习建议。"
    if weak:
        return (
            f"当前薄弱知识点 {len(weak)} 个，建议优先复习：{'、'.join(weak[:4])}。"
            "先看错题解析，再连续做 3-5 道同类题巩固。"
        )
    accuracy = float(stats.get("accuracy") or 0)
    if accuracy >= 85:
        return "整体掌握较好。建议保持每日练习，并尝试更高难度或综合题，巩固知识迁移能力。"
    if accuracy >= 65:
        return "整体基础较稳。建议重点突破正确率 60%-80% 的知识点，配合错题重练提升稳定性。"
    return "整体正确率偏低。建议从基础概念和方程式重新梳理，先做简单题建立信心，再逐步提高难度。"


def build_report_pdf(profile: dict, stats: dict, trend: list, knowledge: dict, heatmap: dict, recent: list) -> bytes:
    name = profile.get("name") or profile.get("username") or "同学"
    username = profile.get("username") or ""
    now = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    doc = pymupdf.open()

    # 第一页：概览 + 趋势 + 知识点
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    _header(page, name, username, now)
    y = _summary_cards(page, 112, stats)

    y = _section(page, y + 6, "近 14 天做题趋势", f"共 {len(trend)} 天")
    _trend_chart(page, y, trend)
    y += 176

    details = knowledge.get("details") or []
    note = f"展示 {min(len(details), 8)}/{len(details)} 个知识点" if details else ""
    y = _section(page, y + 6, "知识点掌握度", note)
    _knowledge_rows(page, y, details)

    # 第二页：最近练习 + 活跃度 + 建议
    page2 = doc.new_page(width=PAGE_W, height=PAGE_H)
    _header(page2, name, username, now, height=82)
    y2 = 112
    y2 = _section(page2, y2, "最近练习", f"近 {len(recent)} 条")
    y2 = _recent_rows(page2, y2, recent)
    y2 += 8
    y2 = _section(page2, y2 + 6, "学习活跃度")
    active = heatmap.get("active_days") or 0
    days = heatmap.get("days") or 91
    _draw(
        page2, M, y2 + 6,
        f"近 {days} 天活跃 {active} 天，共完成 {stats.get('total_questions', 0)} 道练习。",
        9, INK,
    )
    y2 += 34
    y2 = _section(page2, y2 + 4, "学习建议")
    lines = _wrap_lines(_suggestion(knowledge, stats), PAGE_W - 2 * M, 9.5)
    for i, line in enumerate(lines[:5]):
        _draw(page2, M, y2 + i * 18, line, 9.5, INK)

    total_pages = doc.page_count
    for i, p in enumerate(doc, 1):
        _footer(p, i, total_pages)
    data = doc.tobytes()
    doc.close()
    return data
