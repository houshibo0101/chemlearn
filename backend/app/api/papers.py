# -*- coding: utf-8 -*-
"""
套卷练习 API

流程：
  1. 任何人可上传试卷（PDF/txt/md），学生上传后状态是 pending，需管理员审核
  2. 管理员上传/审核通过 → 触发后台任务：AI 结构化 → 题目入库 → 渲染 HTML
  3. 学生点开套卷 → /page 返回做题页 → 交卷 POST /submit → 判分 + 错题入错题本
"""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    Paper, PaperAttempt, PaperStatus, PaperGenStatus, User,
)
from app.services import paper_service

router = APIRouter(prefix="/papers", tags=["套卷练习"])

MAX_SIZE = 20 * 1024 * 1024          # 单份试卷 20MB
ALLOWED_EXT = ("pdf", "txt", "md")


def _is_admin(user: User) -> bool:
    return (user.role or "").lower() == "admin"


def _is_teacher(user: User) -> bool:
    return (user.role or "").lower() in ("admin", "teacher")


def _brief(p: Paper, for_admin: bool = False) -> dict:
    data = {
        "id": p.id,
        "title": p.title,
        "province": p.province,
        "year": p.year,
        "exam_type": p.exam_type,
        "status": p.status.value if hasattr(p.status, "value") else p.status,
        "gen_status": p.gen_status.value if hasattr(p.gen_status, "value") else p.gen_status,
        "gen_error": p.gen_error,
        "duration": p.duration,
        "total_score": p.total_score,
        "question_count": p.question_count,
        "progress": p.progress or 0,
        "progress_text": p.progress_text or "",
        "gen_logs": p.gen_logs or [],
        "view_count": p.view_count or 0,
        "attempt_count": p.attempt_count or 0,
        "uploader_id": p.uploader_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "source_filename": p.source_filename,
        "ready": p.gen_status == PaperGenStatus.DONE and bool(p.questions_json),
    }
    if for_admin:
        data.update({
            "review_note": p.review_note,
            "file_size": p.file_size,
            "gen_at": p.gen_at.isoformat() if p.gen_at else None,
            "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        })
    return data


# ---------------------------------------------------------------- 列表

@router.get("", summary="套卷列表")
async def list_papers(
    status: str | None = None,
    mine: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Paper)
    admin_view = _is_admin(current_user) and (status is not None or mine is False)

    if status:
        if not _is_admin(current_user):
            raise HTTPException(status_code=403, detail="只有管理员能按审核状态筛选")
        q = q.where(Paper.status == PaperStatus(status))
    elif mine:
        q = q.where(Paper.uploader_id == current_user.id)
    elif _is_admin(current_user):
        pass  # 管理员默认看全部
    else:
        # 学生/教师：只看审核通过且已生成完的
        q = q.where(
            Paper.status == PaperStatus.APPROVED,
            Paper.gen_status == PaperGenStatus.DONE,
            Paper.is_public.is_(True),
        )

    rows = (await db.execute(q.order_by(desc(Paper.created_at)).limit(200))).scalars().all()

    # 我的作答记录（用于列表上显示"已做 82 分"）
    my_best = {}
    try:
        att = (await db.execute(
            select(PaperAttempt.paper_id, func.max(PaperAttempt.score))
            .where(PaperAttempt.user_id == current_user.id)
            .group_by(PaperAttempt.paper_id)
        )).all()
        my_best = {pid: sc for pid, sc in att}
    except Exception:
        pass

    out = []
    for p in rows:
        d = _brief(p, for_admin=admin_view)
        if p.id in my_best:
            d["my_best_score"] = my_best[p.id]
        out.append(d)

    pending_count = 0
    if _is_admin(current_user):
        pending_count = (await db.execute(
            select(func.count(Paper.id)).where(Paper.status == PaperStatus.PENDING)
        )).scalar() or 0

    return {"items": out, "total": len(out), "pending_count": pending_count}


# ---------------------------------------------------------------- 上传

@router.post("/upload", summary="上传试卷（学生需审核）")
async def upload_paper(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    province: str = Form(""),
    year: str = Form(""),
    exam_type: str = Form("高考真题"),
    duration: int = Form(75),
    total_score: int = Form(100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "paper.pdf"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="只支持 PDF / TXT / MD 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件是空的")
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="文件超过 20MB，请压缩后再上传")

    try:
        year_int = int(year) if str(year).strip() else None
    except ValueError:
        year_int = None

    paper = Paper(
        title=(title.strip() or filename.rsplit(".", 1)[0])[:200],
        province=(province or "").strip()[:32] or None,
        year=year_int,
        exam_type=(exam_type or "高考真题")[:32],
        source_filename=filename[:255],
        file_size=len(content),
        uploader_id=current_user.id,
        duration=max(10, min(300, int(duration or 75))),
        total_score=max(10, min(300, int(total_score or 100))),
        status=PaperStatus.PENDING,
        gen_status=PaperGenStatus.WAITING,
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    # 落盘
    paper_service.ensure_dirs()
    rel = f"papers/src/{paper.id}-{uuid.uuid4().hex[:8]}.{ext}"
    with open(os.path.join(paper_service.UPLOAD_ROOT, rel), "wb") as f:
        f.write(content)
    paper.source_path = rel

    # 管理员/教师上传直接通过并开始生成；学生上传等审核
    if _is_teacher(current_user):
        paper.status = PaperStatus.APPROVED
        paper.reviewer_id = current_user.id
        paper.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        background.add_task(paper_service.generate_paper, paper.id)
        msg = "上传成功，正在生成做题页（约 1-2 分钟）"
    else:
        await db.commit()
        msg = "上传成功，等待管理员审核通过后自动生成做题页"

    return {"id": paper.id, "status": paper.status.value, "message": msg}


# ---------------------------------------------------------------- 审核

@router.post("/{paper_id}/review", summary="【管理员】审核试卷")
async def review_paper(
    paper_id: int,
    background: BackgroundTasks,
    action: str = Form(...),                 # approve / reject
    note: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员能审核")

    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    if action == "reject":
        paper.status = PaperStatus.REJECTED
        paper.review_note = (note or "内容不符合要求")[:500]
        paper.reviewer_id = current_user.id
        paper.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "rejected"}

    paper.status = PaperStatus.APPROVED
    paper.review_note = (note or "")[:500]
    paper.reviewer_id = current_user.id
    paper.reviewed_at = datetime.now(timezone.utc)
    paper.gen_status = PaperGenStatus.WAITING
    paper.gen_error = None
    await db.commit()

    background.add_task(paper_service.generate_paper, paper.id)
    return {"status": "approved", "message": "已通过，开始生成做题页"}


@router.post("/{paper_id}/regenerate", summary="【管理员】重新生成")
async def regenerate(
    paper_id: int,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员能重新生成")
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    paper.gen_status = PaperGenStatus.WAITING
    paper.gen_error = None
    await db.commit()
    background.add_task(paper_service.generate_paper, paper.id)
    return {"message": "已重新开始生成"}


# ---------------------------------------------------------------- 做题页

@router.get("/{paper_id}/page", response_class=HTMLResponse, summary="做题页（HTML）")
async def paper_page(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        return HTMLResponse("<h3>试卷不存在</h3>", status_code=404)
    if paper.status != PaperStatus.APPROVED or paper.gen_status != PaperGenStatus.DONE:
        return HTMLResponse("<h3>这份试卷还没有准备好</h3>", status_code=409)
    html = paper_service.render_html(paper, paper.questions_json or [])
    return HTMLResponse(html)


@router.get("/{paper_id}/pageimg/{page_no}", summary="原卷页面图（做题页配图）")
async def page_image(paper_id: int, page_no: int):
    """做题页里带图的题会引用这里：文字抽取拿不到装置图/流程图，只能显示原卷该页"""
    path = paper_service.page_image_path(paper_id, page_no)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="页面图不存在")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{paper_id}/questions", summary="套卷题目明细（校对答案用）")
async def paper_questions(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员校对标准答案用：返回每题的题干、选项、答案、解析"""
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    if not _is_admin(current_user) and paper.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="没有权限查看")

    return {
        "id": paper.id,
        "title": paper.title,
        "total_score": paper.total_score,
        "items": [{
            "no": q.get("no"),
            "type": q.get("type"),
            "title": q.get("title"),
            "options": q.get("options") or [],
            "answer": q.get("answer") or "",
            "analysis": q.get("analysis") or "",
            "score": q.get("score") or 0,
            "page": q.get("page"),
            "has_figure": q.get("has_figure"),
        } for q in (paper.questions_json or [])],
    }


@router.patch("/{paper_id}/questions/{no}", summary="【管理员】修改单题答案/解析")
async def update_question(
    paper_id: int,
    no: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修正 AI 提取错误的标准答案——判分准确性的根本在这里"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员能校对")
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")

    questions = list(paper.questions_json or [])
    target = next((q for q in questions if int(q.get("no") or 0) == no), None)
    if not target:
        raise HTTPException(status_code=404, detail="没有这道题")

    for field in ("answer", "analysis", "title"):
        if field in payload:
            target[field] = str(payload[field] or "")
    if "score" in payload:
        try:
            target["score"] = max(0, int(payload["score"]))
        except (TypeError, ValueError):
            pass

    paper.questions_json = questions
    # JSON 列默认不做变更追踪，改了内部元素必须显式标记，否则 commit 不会写库
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(paper, "questions_json")
    # 同步到题库表，错题本/学习报告读的是那边
    qid = target.get("question_id")
    if qid:
        from app.models import Question
        row = await db.get(Question, qid)
        if row:
            row.answer = target.get("answer") or "—"
            row.analysis = target.get("analysis") or ""
            row.title = (target.get("title") or "")[:500]

    # 重新渲染做题页（分值/答案会显示在页面上）
    paper.html_path = paper_service.write_html(
        paper.id, paper_service.render_html(paper, questions)
    )
    await db.commit()
    return {"ok": True, "answer": target.get("answer")}


@router.post("/{paper_id}/start", summary="开始答题（服务端计时，防刷新重置）")
async def start_paper(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """进入做题页时调用：返回剩余秒数。

    计时基准放在服务端，前端只负责显示——刷新页面、切后台、改系统时间都不会
    让倒计时重置或变慢（浏览器会把后台标签的定时器降到 1 次/分钟）。
    """
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    if paper.status != PaperStatus.APPROVED or paper.gen_status != PaperGenStatus.DONE:
        raise HTTPException(status_code=409, detail="试卷还没准备好")

    row = (await db.execute(
        select(PaperAttempt).where(
            PaperAttempt.paper_id == paper_id,
            PaperAttempt.user_id == current_user.id,
            PaperAttempt.status == "doing",
        ).order_by(desc(PaperAttempt.id))
    )).scalars().first()

    now = datetime.now(timezone.utc)
    if not row:
        row = PaperAttempt(
            paper_id=paper_id,
            user_id=current_user.id,
            status="doing",
            started_at=now,
            total_score=paper.total_score or 0,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

    total = (paper.duration or 75) * 60
    started = row.started_at or now
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (now - started).total_seconds()

    return {
        "attempt_id": row.id,
        "duration_sec": total,
        "remain_sec": max(0, int(total - elapsed)),
        "elapsed_sec": int(elapsed),
        "switch_count": row.switch_count or 0,
    }


@router.post("/{paper_id}/view", summary="访问计数")
async def view_paper(paper_id: int, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if paper:
        paper.view_count = (paper.view_count or 0) + 1
        await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- 交卷

@router.post("/{paper_id}/submit", summary="交卷判分（错题入错题本）")
async def submit_paper(
    paper_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    if paper.gen_status != PaperGenStatus.DONE:
        raise HTTPException(status_code=409, detail="试卷还没生成完")

    answers = payload.get("answers") or {}
    self_judge = payload.get("self_judge") or {}
    switch_count = int(payload.get("switch_count") or 0)
    attempt_id = payload.get("attempt_id")

    # 用时以服务端记录的 started_at 为准，前端传的 duration_sec 只作兜底
    now = datetime.now(timezone.utc)
    attempt = None
    if attempt_id:
        attempt = await db.get(PaperAttempt, int(attempt_id))
    if attempt is None or attempt.user_id != current_user.id or attempt.status != "doing":
        attempt = (await db.execute(
            select(PaperAttempt).where(
                PaperAttempt.paper_id == paper_id,
                PaperAttempt.user_id == current_user.id,
                PaperAttempt.status == "doing",
            ).order_by(desc(PaperAttempt.id))
        )).scalars().first()

    elapsed = int(payload.get("duration_sec") or 0)
    if attempt and attempt.started_at:
        started = attempt.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed = int((now - started).total_seconds())

    limit = (paper.duration or 75) * 60
    overtime = elapsed > limit + 60          # 留 1 分钟容错（网络/提交耗时）

    result = await paper_service.judge(paper, answers, self_judge)

    if attempt is None:
        attempt = PaperAttempt(paper_id=paper.id, user_id=current_user.id, started_at=now)

    attempt.status = "submitted"
    attempt.answers = answers
    attempt.score = result["score"]
    attempt.total_score = result["total_score"]
    attempt.correct_count = result["correct_count"]
    attempt.wrong_count = result["wrong_count"]
    attempt.duration_sec = elapsed
    attempt.self_judge = self_judge
    attempt.switch_count = max(switch_count, attempt.switch_count or 0)
    attempt.overtime = overtime
    attempt.submitted_at = now

    db.add(attempt)
    paper.attempt_count = (paper.attempt_count or 0) + 1
    await db.commit()

    await paper_service.sync_records(db, paper, current_user.id, result, elapsed)

    result["overtime"] = overtime
    result["switch_count"] = attempt.switch_count
    result["elapsed_sec"] = elapsed
    return result


@router.get("/{paper_id}/attempts", summary="我的作答记录")
async def my_attempts(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(PaperAttempt)
        .where(PaperAttempt.paper_id == paper_id, PaperAttempt.user_id == current_user.id)
        .order_by(desc(PaperAttempt.submitted_at))
        .limit(20)
    )).scalars().all()
    return {"items": [{
        "id": a.id,
        "score": a.score,
        "total_score": a.total_score,
        "correct_count": a.correct_count,
        "wrong_count": a.wrong_count,
        "duration_sec": a.duration_sec,
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
    } for a in rows]}


# ---------------------------------------------------------------- 删除

@router.delete("/{paper_id}", summary="删除套卷")
async def delete_paper(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    if not _is_admin(current_user) and paper.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己上传的试卷")

    # 清理文件（失败忽略）
    try:
        if paper.source_path:
            p = os.path.join(paper_service.UPLOAD_ROOT, paper.source_path)
            if os.path.isfile(p):
                os.remove(p)
        if paper.html_path:
            p = os.path.join(paper_service.UPLOAD_ROOT, paper.html_path)
            if os.path.isfile(p):
                os.remove(p)
    except OSError:
        pass

    await db.delete(paper)
    await db.commit()
    return {"ok": True}
