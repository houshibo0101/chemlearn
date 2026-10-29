# -*- coding: utf-8 -*-
"""
套卷生成服务

链路：PDF → 文本 → AI 结构化题目 JSON → 写入 questions（可得 question_id）
      → 用固定模板渲染成独立 HTML 做题页

为什么不让 AI 直接产出 HTML：
  AI 生成的 HTML 样式不可控、判分逻辑容易写错、题目无法回填到题库，
  错题本也就无法关联。所以只让 AI 做「文本 → 结构化 JSON」，渲染交给模板。
"""
import asyncio
import io
import json
import os
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import (
    Paper, PaperGenStatus, PaperStatus, Question, QuestionType, Difficulty,
    PracticeRecord, WrongQuestion,
)
from app.services.paper_template import TEMPLATE

# ---------------------------------------------------------------- 路径

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_ROOT = os.path.join(BACKEND_DIR, "uploads")
PAPER_ROOT = os.path.join(UPLOAD_ROOT, "papers")


def ensure_dirs() -> None:
    for sub in ("src", "html"):
        os.makedirs(os.path.join(PAPER_ROOT, sub), exist_ok=True)


# ---------------------------------------------------------------- PDF → 文本 / 页面图

def render_pdf_pages(content: bytes, dpi: int = 150) -> list[bytes]:
    """把 PDF 每页渲染成 PNG。

    两个用途：① 扫描版走视觉识别；② 做题页里给带图的题附上原卷页面
    （文字抽取拿不到装置图/流程图/曲线图，只能靠渲染图补）。
    """
    try:
        import pymupdf
    except ImportError:
        raise RuntimeError("服务器未安装 pymupdf，无法处理 PDF 页面")
    doc = pymupdf.open(stream=content, filetype="pdf")
    if doc.page_count > 40:
        raise RuntimeError(f"这份 PDF 有 {doc.page_count} 页，超过 40 页上限，建议拆分后再传")
    out = []
    for i in range(doc.page_count):
        pix = doc[i].get_pixmap(dpi=dpi)
        out.append(pix.tobytes("png"))
    return out


def save_page_images(paper_id: int, pngs: list[bytes]) -> None:
    """存到 uploads/papers/pages/{paper_id}/p{n}.png"""
    d = os.path.join(PAPER_ROOT, "pages", str(paper_id))
    os.makedirs(d, exist_ok=True)
    for i, png in enumerate(pngs, 1):
        with open(os.path.join(d, f"p{i}.png"), "wb") as f:
            f.write(png)


def page_image_path(paper_id: int, page_no: int) -> str:
    return os.path.join(PAPER_ROOT, "pages", str(paper_id), f"p{page_no}.png")


def extract_pdf_pages_text(content: bytes) -> list[str]:
    """按页提取文字（文字型 PDF）"""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise RuntimeError("服务器未安装 PyPDF2，无法解析 PDF")
    try:
        reader = PdfReader(io.BytesIO(content))
        out = []
        for page in reader.pages:
            try:
                out.append(page.extract_text() or "")
            except Exception:
                out.append("")
        return out
    except Exception as e:
        raise RuntimeError(f"PDF 解析失败：{e}")


def extract_pdf_text(content: bytes) -> str:
    """提取 PDF 文字；扫描件（图片型）会返回空串，由调用方决定是否走 OCR"""
    return "\n".join(extract_pdf_pages_text(content)).strip()


def extract_text_any(content: bytes, ext: str) -> str:
    """支持 pdf / txt / md（同步版，仅用于有文字层的文件）"""
    if ext == "pdf":
        return extract_pdf_text(content)
    if ext in ("txt", "md"):
        return content.decode("utf-8", errors="ignore").strip()
    raise RuntimeError(f"不支持的文件类型：{ext}")


# ---------------------------------------------------------------- 扫描版 PDF 视觉识别

OCR_PROMPT = (
    "把这张试卷图片里的所有文字原样识别出来，包括题号、题干、选项、分值、"
    "以及可能出现的答案与解析。不要总结，不要加解释，不要漏行。"
)


async def ocr_pages(pngs: list[bytes], on_page=None) -> list[str]:
    """逐页视觉识别，返回与输入等长的文本列表（失败的页给空串）

    化学试卷里公式多，直接 OCR 常常丢下标，用多模态模型识别质量明显更好。
    页数多时并发 3 页，避免把上游打爆。
    on_page(done, total) 用于上报进度。
    """
    if not pngs:
        return []
    import base64

    pages = len(pngs)
    print(f"[套卷] {pages} 页走视觉识别（较慢）")
    sem = asyncio.Semaphore(3)
    finished = 0

    async with httpx.AsyncClient(timeout=max(settings.AI_TIMEOUT, 180)) as client:
        async def one(idx: int) -> str:
            nonlocal finished
            async with sem:
                b64 = base64.b64encode(pngs[idx]).decode()
                try:
                    resp = await client.post(
                        f"{settings.AI_API_BASE}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                        json={
                            "model": settings.AI_MODEL,
                            "messages": [{
                                "role": "user",
                                "content": [
                                    {"type": "image_url",
                                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                                    {"type": "text", "text": OCR_PROMPT},
                                ],
                            }],
                            "temperature": 0.1,
                            "max_tokens": 4000,
                        },
                    )
                    resp.raise_for_status()
                    return (resp.json()["choices"][0]["message"].get("content") or "").strip()
                finally:
                    finished += 1
                    if on_page:
                        try:
                            await on_page(finished, pages)
                        except Exception:
                            pass

        results = await asyncio.gather(*[one(i) for i in range(pages)], return_exceptions=True)

    texts = []
    failed = 0
    for r in results:
        if isinstance(r, str) and r:
            texts.append(r)
        else:
            texts.append("")
            failed += 1
    if failed == pages:
        raise RuntimeError("视觉识别没有返回内容，请检查 PDF 是否正常")
    if failed:
        print(f"[套卷] 有 {failed} 页识别失败，已跳过")
    return texts


def build_paged_text(pages_text: list[str]) -> str:
    """拼接时标上页码，让 AI 能给出每题所在的页（做题页据此显示原卷配图）"""
    parts = []
    for i, t in enumerate(pages_text, 1):
        if (t or "").strip():
            parts.append(f"【第{i}页】\n{t.strip()}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- AI 结构化

AI_SYSTEM = (
    "你是高中化学试卷结构化专家。你的任务是把试卷文字整理成严格合法的 JSON，"
    "不添加解释性文字，不编造试卷里没有的题目。"
)

AI_PROMPT = """把下面这段化学试卷文本转成 JSON，只输出 JSON 本身。

输出格式：
{{"questions": [
  {{
    "no": 1,
    "type": "single",
    "title": "题干文字",
    "content": "补充材料或图表说明，可为空",
    "options": [{{"key": "A", "text": "选项内容"}}],
    "answer": "A",
    "analysis": "解析文字，可空",
    "score": 3,
    "knowledge_point": "知识点",
    "page": 3,
    "has_figure": false
  }}
]}}

硬性要求：
1. type 只能是 single(单选) / multiple(多选) / fill(填空) / calculation(计算) / subjective(简答)
2. 选择题必须有 options；非选择题 options 给 []
3. 多选题 answer 写成 "AB" 这种形式
4. 化学式一律用 Unicode 下标（H₂SO₄、CO₂、Ca²⁺），不要用 LaTeX 或 $...$
5. score：题干标了分值就用标注，没标就按整卷总分平均估算
6. answer 确实无法确定的题，answer 留空字符串，不要猜
7. 文本残缺、看不清的题直接跳过，不要补全
8. 题目编号尽量沿用原文的题号
9. page：该题所在的页码，取自文本里的【第N页】标记，取不到就填 1
10. has_figure：题目需要看图形才能作答（装置图、流程图、曲线图、表格、结构式）时为 true，纯文字题 false

试卷名：{title}
整卷总分：{total_score} 分

试卷文本：
---
{text}
---
"""


def _split_chunks(text: str, size: int = 6000) -> list[str]:
    """按题号边界切块，避免把一道题劈成两半"""
    if len(text) <= size:
        return [text]
    chunks, buf = [], ""
    for line in text.splitlines(True):
        if len(buf) + len(line) > size and buf.strip():
            chunks.append(buf)
            buf = ""
        buf += line
    if buf.strip():
        chunks.append(buf)
    # 太长再硬切
    out = []
    for c in chunks:
        while len(c) > size * 2:
            out.append(c[: size * 2])
            c = c[size * 2:]
        out.append(c)
    return out


def _fix_escapes(s: str) -> str:
    """修复 AI 输出的非法转义：试卷里的 `\\%` `\\(` 之类会让 json 解析直接失败。
    只转义非法的（保留 \\" \\\\ \\/ \\b \\f \\n \\r \\t \\uXXXX）。
    """
    return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", s)


def _parse_json_any(raw: str):
    """把 AI 输出解析成 Python 对象（dict 或 list），做多层容错"""
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)

    candidates = [s, _fix_escapes(s)]
    for base in list(candidates):
        i, j = base.find("{"), base.rfind("}")
        if i >= 0 and j > i:
            candidates.append(base[i: j + 1])
        i, j = base.find("["), base.rfind("]")
        if i >= 0 and j > i:
            candidates.append(base[i: j + 1])

    last_err = None
    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"AI 返回的内容不是合法 JSON（{last_err}）")


def _loads_json(raw: str) -> list:
    """取题目数组（AI 常包成 {"questions": [...]}）"""
    data = _parse_json_any(raw)
    if isinstance(data, dict):
        return data.get("questions") or data.get("data") or []
    return data if isinstance(data, list) else []


async def ai_structure(text: str, title: str, total_score: int, on_chunk=None) -> tuple[list[dict], list[str]]:
    """调用 OpenAI 兼容接口，把文本转题目数组。

    返回 (题目列表, 警告列表)。单段失败不拖垮整份卷——只要能拿到部分题目就先出卷，
    失败的段数记到警告里给用户看。
    """
    if not settings.AI_API_KEY:
        raise RuntimeError("AI 服务未配置（缺少 AI_API_KEY），无法自动生成题目")

    # 套卷生成走 AI_MODEL（生成网页用豆包）；解析类才用 AI_EXPLAIN_MODEL
    model = settings.AI_MODEL
    chunks = _split_chunks(text)
    questions: list[dict] = []
    warnings: list[str] = []
    print(f"[套卷] 使用模型 {model} 解析 {len(chunks)} 段文本")
    async with httpx.AsyncClient(timeout=max(settings.AI_TIMEOUT, 180)) as client:
        for idx, chunk in enumerate(chunks, 1):
            prompt = AI_PROMPT.format(title=title, total_score=total_score, text=chunk)
            try:
                resp = await client.post(
                    f"{settings.AI_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": AI_SYSTEM},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 8000,
                    },
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]
                part = _loads_json(raw)
                questions.extend(part)
                print(f"[套卷] 第 {idx}/{len(chunks)} 段解析出 {len(part)} 题")
                if on_chunk:
                    try:
                        await on_chunk(idx, len(chunks), len(part))
                    except Exception:
                        pass
            except Exception as e:
                warnings.append(f"第 {idx}/{len(chunks)} 段解析失败：{e}")
                print(f"[套卷] 第 {idx}/{len(chunks)} 段解析失败：{e}")
                if on_chunk:
                    try:
                        await on_chunk(idx, len(chunks), 0)
                    except Exception:
                        pass

    if not questions:
        raise RuntimeError("；".join(warnings) or "AI 没有返回任何题目")
    return questions, warnings


# ---------------------------------------------------------------- 归一化

def _clean_text(s) -> str:
    """去掉 AI 残留的转义反斜杠：5\\% → 5%，\\(1\\) → (1)"""
    if not s:
        return ""
    return re.sub(r"\\([%_()^&{}$#\s])", r"\1", str(s))


def normalize_question(q: dict, fallback_no: int) -> dict | None:
    if not isinstance(q, dict):
        return None
    title = _clean_text(q.get("title") or q.get("content")).strip()
    if not title:
        return None
    qtype = str(q.get("type") or "single").lower()
    if qtype not in ("single", "multiple", "fill", "calculation", "subjective"):
        qtype = "single" if q.get("options") else "fill"

    options = []
    for o in (q.get("options") or []):
        if isinstance(o, dict):
            key = str(o.get("key") or o.get("value") or "").strip()
            text = _clean_text(o.get("text") or o.get("value")).strip()
            if key and text:
                options.append({"key": key[:4], "text": text})
        elif isinstance(o, str):
            options.append({"key": chr(65 + len(options)), "text": o.strip()})

    try:
        no = int(str(q.get("no") or fallback_no).strip())
    except (TypeError, ValueError):
        no = fallback_no
    try:
        score = int(float(q.get("score") or 0))
    except (TypeError, ValueError):
        score = 0

    try:
        page = int(str(q.get("page") or 1).strip())
    except (TypeError, ValueError):
        page = 1

    return {
        "no": no,
        "raw_no": no,          # 原始题号：用于跨段去重（试卷常带答案页，同一题会出现两次）
        "type": qtype,
        "title": title,
        "content": _clean_text(q.get("content")).strip() if q.get("content") != title else "",
        "options": options,
        "answer": _clean_text(q.get("answer")).strip(),
        "analysis": _clean_text(q.get("analysis")).strip(),
        "score": score,
        "knowledge_point": _clean_text(q.get("knowledge_point")).strip(),
        "page": max(1, page),
        "has_figure": bool(q.get("has_figure")),
    }


def normalize_all(raw_questions: list[dict], total_score: int) -> list[dict]:
    out = []
    for i, q in enumerate(raw_questions, 1):
        nq = normalize_question(q, i)
        if nq:
            out.append(nq)

    # 试卷里常有「题面页 + 答案页」，同一题会被解析两遍（题号相同、表述略有差异）。
    # 按原始题号分组，取信息量最大的一条为主，缺的答案/解析从同组另一条补上。
    groups: dict[int, list[dict]] = {}
    for q in out:
        groups.setdefault(q["raw_no"], []).append(q)

    merged: list[dict] = []
    for no, group in groups.items():
        group.sort(key=lambda x: (len(x["options"]), len(x["title"])), reverse=True)
        main = group[0]
        for other in group[1:]:
            if not main.get("answer") and other.get("answer"):
                main["answer"] = other["answer"]
            if not main.get("analysis") and other.get("analysis"):
                main["analysis"] = other["analysis"]
            if not main.get("options") and other.get("options"):
                main["options"] = other["options"]
            if not main.get("knowledge_point") and other.get("knowledge_point"):
                main["knowledge_point"] = other["knowledge_point"]
        merged.append(main)

    merged.sort(key=lambda x: x["raw_no"])

    # 没标分值的按平均分补，余数补给前面的题，保证分值和等于总分
    if merged:
        missing = [q for q in merged if not q["score"]]
        if missing:
            base = max(1, total_score // len(merged))
            for q in missing:
                q["score"] = base
        diff = total_score - sum(q["score"] for q in merged)
        if diff > 0:
            for q in merged[:diff]:
                q["score"] += 1

    # 重新编号为 1..N，避免题号跳号导致导航怪
    for i, q in enumerate(merged, 1):
        q["no"] = i
    return merged


# ---------------------------------------------------------------- 写题库 + 渲染

QTYPE_MAP = {
    "single": QuestionType.SINGLE,
    "multiple": QuestionType.MULTIPLE,
    "fill": QuestionType.FILL,
    "calculation": QuestionType.CALCULATION,
    "subjective": QuestionType.SUBJECTIVE,
}


async def save_questions(db, paper: Paper, questions: list[dict]) -> None:
    """把题目写进 questions 表，回填 question_id（错题本要靠它关联）"""
    # 重新生成时题数可能变少，先清掉这套卷多出来的旧题目（连带错题/记录引用）
    from sqlalchemy import delete
    keep_codes = {f"P{paper.id}-{q['no']:02d}" for q in questions}
    stale = (await db.execute(
        select(Question).where(Question.question_code.like(f"P{paper.id}-%"))
    )).scalars().all()
    for row in stale:
        if row.question_code not in keep_codes:
            await db.execute(delete(WrongQuestion).where(WrongQuestion.question_id == row.id))
            await db.execute(delete(PracticeRecord).where(PracticeRecord.question_id == row.id))
            await db.delete(row)
    if stale:
        await db.flush()

    for q in questions:
        code = f"P{paper.id}-{q['no']:02d}"
        existed = (await db.execute(
            select(Question).where(Question.question_code == code)
        )).scalar_one_or_none()

        if existed:  # 重新生成时复用，避免重复入库
            existed.title = q["title"][:500]
            existed.content = q["content"]
            existed.question_type = QTYPE_MAP.get(q["type"], QuestionType.SINGLE)
            existed.difficulty = Difficulty.MEDIUM
            existed.grade = "高三"
            existed.knowledge_point = q["knowledge_point"][:128] if q["knowledge_point"] else None
            existed.options = json.dumps(q["options"], ensure_ascii=False) if q["options"] else None
            existed.answer = q["answer"] or "—"
            existed.analysis = q["analysis"]
            existed.source = f"套卷《{paper.title}》第 {q['no']} 题"
            q["question_id"] = existed.id
        else:
            row = Question(
                question_code=code,
                title=q["title"][:500],
                content=q["content"],
                question_type=QTYPE_MAP.get(q["type"], QuestionType.SINGLE),
                difficulty=Difficulty.MEDIUM,
                grade="高三",
                knowledge_point=q["knowledge_point"][:128] if q["knowledge_point"] else None,
                options=json.dumps(q["options"], ensure_ascii=False) if q["options"] else None,
                answer=q["answer"] or "—",
                analysis=q["analysis"],
                source=f"套卷《{paper.title}》第 {q['no']} 题",
                creator_id=paper.uploader_id,
            )
            db.add(row)
            await db.flush()
            q["question_id"] = row.id
    await db.commit()


def _rescale_scores(questions: list[dict], target: int) -> int:
    """把题目分值之和缩放到目标总分。

    AI 给的分值之和几乎不可能正好等于用户填的总分（常见 98、119、106），
    差额会让「全对也拿不到满分」。这里一律对齐到 target，成绩单才自洽。
    """
    if not questions or target <= 0:
        return sum(int(q.get("score") or 0) for q in questions)

    real = sum(int(q.get("score") or 0) for q in questions)
    if real <= 0 or real == target:
        return real

    factor = target / real
    for q in questions:
        q["score"] = max(1, round(int(q.get("score") or 0) * factor))

    # 舍入误差补齐，保证总和正好等于 target
    diff = target - sum(int(q.get("score") or 0) for q in questions)
    i = 0
    guard = 0
    while diff != 0 and questions and guard < 1000:
        idx = i % len(questions)
        if diff > 0:
            questions[idx]["score"] += 1
            diff -= 1
        elif questions[idx]["score"] > 1:
            questions[idx]["score"] -= 1
            diff += 1
        i += 1
        guard += 1
    return sum(int(q.get("score") or 0) for q in questions)


def render_html(paper: Paper, questions: list[dict]) -> str:
    data = {
        "id": paper.id,
        "title": paper.title,
        "province": paper.province or "",
        "year": paper.year or "",
        "exam_type": paper.exam_type or "",
        "duration": paper.duration or 75,
        "total_score": paper.total_score or 100,
        "questions": questions,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__PAPER_TITLE__", _esc(paper.title)).replace("__PAPER_DATA__", payload)
    return html


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def write_html(paper_id: int, html: str) -> str:
    ensure_dirs()
    rel = f"papers/html/{paper_id}.html"
    path = os.path.join(UPLOAD_ROOT, rel)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return rel


# ---------------------------------------------------------------- 判分

def _norm(s) -> str:
    s = str(s or "").strip().upper()
    s = re.sub(r"\s+", "", s)
    return s.replace("，", ".").replace("。", ".").replace("；", ";")


def _loose_equal(mine: str, answer: str) -> bool:
    """填空/计算题的规则兜底比对（AI 判分不可用时才用）：
    完全一致、互相包含、或数字序列一致（1.7×10⁻⁵ 与 1.7×10^-5 mol/L）都算对。
    """
    a, b = _norm(mine), _norm(answer)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    na = re.findall(r"\d+(?:\.\d+)?", a)
    nb = re.findall(r"\d+(?:\.\d+)?", b)
    return bool(na) and na == nb


GRADE_SYSTEM = "你是高中化学阅卷老师，严格按要点判分，只输出 JSON，不写多余文字。"

GRADE_PROMPT = """逐题判断学生的作答是否正确。

判分原则：
1. 意思正确即算对，不因表述、顺序、繁简、标点不同而判错
2. 化学式 / 离子符号等价写法算对（H⁺ 与 H+、SO₄²⁻ 与 SO4^2-、Ca(OH)₂ 与 Ca(OH)2）
3. 数值题允许有效数字与单位写法差异，但数值本身必须正确；单位错误判错
4. 化学方程式 / 离子方程式：未配平、漏写必要条件（加热、催化剂、↑↓）判错
5. 分小问的题，任何一个小问错就判错
6. 空白、答非所问、只写"不知道"一律判错
7. reason 用不超过 25 个字说明理由，指出关键错因

只输出这种 JSON：
{{"results":[{{"no":1,"correct":true,"reason":"数值与单位均正确"}}]}}

待判题目（题干 / 参考答案 / 学生作答）：
{items}
"""


async def ai_grade_subjective(paper: Paper, answers: dict) -> dict:
    """非选择题交给 AI 阅卷，返回 {题号: {ok, reason, source}}。

    选择题不走这里（精确比对更可靠）。空白答案直接判错，不浪费调用。
    失败时返回空字典，由调用方回退到规则匹配。
    """
    if not settings.AI_API_KEY:
        return {}

    items = []
    for q in (paper.questions_json or []):
        if q.get("type") in ("single", "multiple"):
            continue
        if not (q.get("answer") or "").strip():
            continue
        mine = str(answers.get(str(q.get("no")), "") or "").strip()
        if not mine:
            continue
        items.append({
            "no": q.get("no"),
            "question": (q.get("title") or "")[:500],
            "reference": (q.get("answer") or "")[:300],
            "student": mine[:300],
        })

    if not items:
        return {}

    model = getattr(settings, "AI_EXPLAIN_MODEL", "") or settings.AI_MODEL
    body = json.dumps(items, ensure_ascii=False)
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.AI_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": GRADE_SYSTEM},
                        {"role": "user", "content": GRADE_PROMPT.format(items=body)},
                    ],
                    "temperature": 0,
                    "max_tokens": 2000,
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            data = _parse_json_any(raw)
            results = data.get("results") if isinstance(data, dict) else data
            out = {}
            for r in (results or []):
                try:
                    no = int(r.get("no"))
                except (TypeError, ValueError):
                    continue
                out[no] = {
                    "ok": bool(r.get("correct")),
                    "reason": str(r.get("reason") or "")[:60],
                    "source": "ai",
                }
            print(f"[套卷] AI 判分完成：{len(out)} 题")
            return out
    except Exception as e:
        print(f"[套卷] AI 判分失败，回退规则匹配：{e}")
        return {}


async def judge(paper: Paper, answers: dict, self_judge: dict | None = None) -> dict:
    """服务端判分，分两层：

      · 选择题：严格比对（单选/多选都是标准答案，字符串归一后精确相等，最可靠）
      · 填空/计算/简答：交给 AI 阅卷（能处理表述差异、单位、配平等），
        AI 不可用时才回退到 _loose_equal 规则匹配，并在结果里标注判分来源。

    没有标准答案的题（试卷答案页缺失/AI 没识别出答案）不参与判分，
    也不计入满分，否则学生做对了也会被扣分。
    """
    self_judge = self_judge or {}
    questions = paper.questions_json or []

    # 主观题先让 AI 判（一次请求判完），失败则空字典走规则
    ai_grades = await ai_grade_subjective(paper, answers)

    score = 0
    right = wrong = 0
    gradable_total = 0
    missing_answer = 0
    missing_score = 0
    details = []

    for q in questions:
        no = str(q.get("no"))
        mine = str(answers.get(no, "") or "")
        qtype = q.get("type")
        full = int(q.get("score") or 0)
        has_answer = bool((q.get("answer") or "").strip())

        if not has_answer:
            missing_answer += 1
            missing_score += full
            details.append({
                "no": q.get("no"), "ok": None, "mine": mine, "answer": "",
                "score": full, "question_id": q.get("question_id"),
                "note": "参考答案缺失，未计分",
            })
            continue

        gradable_total += full
        ok = None
        reason = ""
        source = "rule"

        if qtype in ("single", "multiple"):
            ok = bool(mine) and _norm(mine) == _norm(q.get("answer"))
            source = "exact"
            if not ok and mine:
                reason = "与标准答案不一致"
        else:
            ai = ai_grades.get(q.get("no"))
            if ai is not None:
                ok = ai["ok"]
                reason = ai.get("reason") or ""
                source = "ai"
            elif not mine:
                ok = False
                reason = "未作答"
            elif _loose_equal(mine, q.get("answer") or ""):
                ok = True
                reason = "与参考答案一致"
            elif no in self_judge:
                ok = bool(self_judge[no])
                reason = "学生自评"
            else:
                ok = False
                reason = "未匹配到参考答案（建议对照解析核对）"

        if ok is True:
            score += full
            right += 1
        elif ok is False:
            wrong += 1

        details.append({
            "no": q.get("no"),
            "ok": ok,
            "mine": mine,
            "answer": q.get("answer") or "",
            "score": full,
            "question_id": q.get("question_id"),
            "reason": reason,
            "source": source,
        })

    # 满分以用户填的目标分为准（成绩单更符合预期），只在有题缺答案时扣掉那部分分值
    base_total = paper.total_score or gradable_total
    return {
        "score": score,
        "total_score": max(0, base_total - missing_score) or gradable_total,
        "correct_count": right,
        "wrong_count": wrong,
        "missing_answer_count": missing_answer,
        "details": details,
    }


async def sync_records(db, paper: Paper, user_id: int, result: dict, duration_sec: int) -> None:
    """错题写错题本 + 每题写一条练习记录（首页/报告统计都靠它）"""
    questions = {str(q.get("no")): q for q in (paper.questions_json or [])}
    now = datetime.now(timezone.utc)

    for d in result["details"]:
        qid = d.get("question_id")
        if not qid:
            continue
        q = questions.get(str(d["no"])) or {}

        # 练习记录（只记判过的题，避免把"待自评"算进正确率）
        if d.get("ok") is not None:
            db.add(PracticeRecord(
                user_id=user_id,
                question_id=qid,
                source="paper",
                user_answer=d.get("mine") or "",
                is_correct=bool(d.get("ok")),
                score=d["score"] if d.get("ok") else 0,
                total_score=d["score"],
                time_spent=None,
                submitted_at=now,
            ))

        # 错题本
        if d.get("ok") is False:
            row = (await db.execute(
                select(WrongQuestion).where(
                    WrongQuestion.user_id == user_id,
                    WrongQuestion.question_id == qid,
                )
            )).scalar_one_or_none()
            if row:
                row.wrong_count = (row.wrong_count or 1) + 1
                row.user_answer = d.get("mine") or ""
                row.last_wrong_at = now
            else:
                db.add(WrongQuestion(
                    user_id=user_id,
                    question_id=qid,
                    wrong_count=1,
                    user_answer=d.get("mine") or "",
                    last_wrong_at=now,
                ))

    await db.commit()


# ---------------------------------------------------------------- 后台生成

_progress_lock = asyncio.Lock()


async def _set_progress(db, paper, pct, text=None, log=None):
    """更新生成进度与日志（前端轮询展示）。失败不影响主流程。

    加锁是因为「心跳协程」和「分段回调」可能同时写同一条记录。
    """
    try:
        async with _progress_lock:
            paper.progress = max(0, min(100, int(pct)))
            if text:
                paper.progress_text = str(text)[:120]
            if log:
                logs = list(paper.gen_logs or [])
                logs.append({"t": datetime.now().strftime("%H:%M:%S"), "m": str(log)[:200]})
                paper.gen_logs = logs[-15:]
            await db.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[套卷] 进度写入失败：{e}")


async def _heartbeat(db, paper, pct, label, stop_evt, every: int = 12):
    """长耗时阶段（AI 解析几十秒没动静）定期刷新文字，避免看起来卡死"""
    waited = 0
    while not stop_evt.is_set():
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=every)
            return
        except asyncio.TimeoutError:
            waited += every
            await _set_progress(db, paper, pct, f"{label}（已等 {waited} 秒）")


async def generate_paper(paper_id: int) -> None:
    """后台任务入口：自己开 session，失败也要把状态写回去"""
    async with AsyncSessionLocal() as db:
        paper = await db.get(Paper, paper_id)
        if not paper:
            return
        paper.gen_status = PaperGenStatus.RUNNING
        paper.gen_error = None
        paper.progress = 1
        paper.progress_text = "准备中"
        paper.gen_logs = []
        await db.commit()
        await _set_progress(db, paper, 3, "读取试卷文件", "开始处理")
        t0 = datetime.now(timezone.utc)

        try:
            pdf_path = os.path.join(UPLOAD_ROOT, paper.source_path or "")
            if not os.path.isfile(pdf_path):
                raise RuntimeError("原始试卷文件不存在")

            with open(pdf_path, "rb") as f:
                content = f.read()
            ext = (paper.source_filename or "").rsplit(".", 1)[-1].lower() or "pdf"
            if ext == "pdf":
                # 先渲染页面：OCR 要用，做题页的配图也要用
                await _set_progress(db, paper, 6, "渲染 PDF 页面", "正在把 PDF 每页转成图片")
                pngs = await asyncio.to_thread(render_pdf_pages, content)
                save_page_images(paper.id, pngs)
                await _set_progress(db, paper, 12, f"已渲染 {len(pngs)} 页",
                                    f"页面图已生成，共 {len(pngs)} 页")
                pages_text = await asyncio.to_thread(extract_pdf_pages_text, content)
                if sum(len((t or "").strip()) for t in pages_text) < 30:
                    print("[套卷] 未读到文字层，按扫描版处理")
                    await _set_progress(db, paper, 15, "识别扫描页",
                                        f"没有文字层，开始逐页视觉识别（共 {len(pngs)} 页）")

                    async def on_page(done, total):
                        pct = 15 + int(30 * done / max(1, total))
                        await _set_progress(db, paper, pct, f"识别扫描页 {done}/{total}",
                                            f"第 {done}/{total} 页识别完成")

                    pages_text = await ocr_pages(pngs, on_page=on_page)
                    await _set_progress(db, paper, 46, "文字识别完成",
                                        f"共识别 {len(pages_text)} 页文字")
                else:
                    await _set_progress(db, paper, 46, "已读取文字层",
                                        "PDF 自带文字层，跳过 OCR")
            elif ext in ("txt", "md"):
                pages_text = [content.decode("utf-8", errors="ignore").strip()]
                await _set_progress(db, paper, 46, "已读取文本", "纯文本试卷")
            else:
                raise RuntimeError(f"不支持的文件类型：{ext}")

            text = build_paged_text(pages_text)
            if len(text) < 30:
                raise RuntimeError(
                    "没有从文件里读到文字，可能是纯图片或空白文件。"
                    "请确认 PDF 内容完整，或先把试卷转成 txt"
                )

            await _set_progress(db, paper, 50, "AI 结构化题目", "开始把题目整理成结构化数据")

            async def on_chunk(idx, total, count):
                pct = 50 + int(36 * idx / max(1, total))
                await _set_progress(db, paper, pct, f"解析第 {idx}/{total} 段",
                                    f"第 {idx}/{total} 段解析出 {count} 道题")

            # 解析一段可能几十秒没有进展，用心跳刷新文字
            stop_hb = asyncio.Event()
            hb = asyncio.create_task(_heartbeat(db, paper, 50, "AI 正在解析题目", stop_hb))
            try:
                raw, warnings = await ai_structure(text, paper.title, paper.total_score or 100,
                                                   on_chunk=on_chunk)
            finally:
                stop_hb.set()
                await asyncio.gather(hb, return_exceptions=True)
            questions = normalize_all(raw, paper.total_score or 100)
            if not questions:
                raise RuntimeError("AI 没有识别出任何题目，建议检查文件内容或稍后重试")
            await _set_progress(db, paper, 88, "整理题目",
                                f"结构化完成，共 {len(questions)} 题（去重合并后）")

            real_total = _rescale_scores(questions, paper.total_score or 100)

            await save_questions(db, paper, questions)
            await _set_progress(db, paper, 94, "写入题库", f"题目已入库，总分 {real_total}")

            html = render_html(paper, questions)
            rel = write_html(paper.id, html)

            paper.questions_json = questions
            paper.question_count = len(questions)
            paper.html_path = rel
            # total_score 保持用户上传时填的值（作为满分基准），不要用卷面分值之和覆盖，
            # 否则重新生成时会以旧的错误值为基准，越跑越偏
            paper.gen_status = PaperGenStatus.DONE
            paper.gen_at = datetime.now(timezone.utc)
            if warnings:
                # 部分分段失败但已出卷，把情况记在备注里让管理员知道
                paper.review_note = "；".join(warnings)[:500]
            await db.commit()

            cost = int((datetime.now(timezone.utc) - t0).total_seconds())
            await _set_progress(db, paper, 100, "生成完成",
                                f"完成：{len(questions)} 题 · 总分 {paper.total_score} · 用时 {cost} 秒")
            print(f"[套卷] #{paper.id} 生成完成：{len(questions)} 题"
                  + (f"（{len(warnings)} 段解析失败）" if warnings else ""))
        except Exception as e:
            await db.rollback()
            paper = await db.get(Paper, paper_id)
            if paper:
                paper.gen_status = PaperGenStatus.FAILED
                paper.gen_error = str(e)[:800]
                paper.progress_text = "生成失败"
                logs = list(paper.gen_logs or [])
                logs.append({"t": datetime.now().strftime("%H:%M:%S"),
                             "m": f"失败：{str(e)[:160]}"})
                paper.gen_logs = logs[-15:]
                await db.commit()
            print(f"[套卷] #{paper_id} 生成失败：{e}")
