# -*- coding: utf-8 -*-
"""化学连连看 API

学生：
  GET    /matching/sets                     可玩的关卡列表（含我的最好成绩）
  GET    /matching/sets/{id}                关卡详情（含配对）
  POST   /matching/sets/{id}/records        提交一局成绩
  GET    /matching/sets/{id}/leaderboard    关卡排行榜
  GET    /matching/my/records               我的作答记录

老师 / 管理员：
  GET    /matching/manage/sets              我创建的关卡（管理员看全部）
  POST   /matching/sets                     新建关卡（手动录入）
  PUT    /matching/sets/{id}                修改关卡
  DELETE /matching/sets/{id}                删除关卡
  GET    /matching/manage/sets/{id}/records 某关卡的作答记录
  POST   /matching/import                   上传 xlsx / csv / txt 批量导入
  GET    /matching/import/template          下载导入模板
"""
import io

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile)
from fastapi.responses import Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_teacher_or_admin, get_current_user
from app.models import (MatchingPair, MatchingRecord, MatchingSet, User,
                        UserRole)
from app.models.matching import CATEGORY_LABELS, DIFFICULTY_LABELS
from app.schemas.matching import MatchingRecordIn, MatchingSetIn
from app.services.matching_parser import parse_file

router = APIRouter(prefix="/matching", tags=["化学连连看"])

MAX_PAGE_SIZE = 50


def _iso(value):
    return value.isoformat() if value else None


def _can_manage(user: User, item: MatchingSet) -> bool:
    return user.role == UserRole.ADMIN or item.creator_id == user.id


def _ensure_manageable(user: User, item: MatchingSet):
    if not _can_manage(user, item):
        raise HTTPException(status_code=403, detail="只能管理自己创建的关卡")


def _display_name(user: User) -> str:
    return user.full_name or user.username or ("用户%d" % user.id)


def _set_payload(item: MatchingSet, *, pair_count: int | None = None) -> dict:
    creator_name = None
    creator = getattr(item, "creator", None)
    if creator is not None:
        creator_name = _display_name(creator)
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "category_label": CATEGORY_LABELS.get(item.category, item.category),
        "difficulty": item.difficulty,
        "difficulty_label": DIFFICULTY_LABELS.get(item.difficulty, item.difficulty),
        "grade": item.grade,
        "is_active": bool(item.is_active),
        "creator_id": item.creator_id,
        "creator_name": creator_name,
        "play_count": item.play_count or 0,
        "pair_count": pair_count if pair_count is not None else len(item.pairs or []),
        "created_at": _iso(item.created_at),
        "updated_at": _iso(item.updated_at),
    }


def _pair_payload(pair: MatchingPair) -> dict:
    return {
        "id": pair.id,
        "left_text": pair.left_text,
        "right_text": pair.right_text,
        "hint": pair.hint,
        "order_index": pair.order_index,
    }


async def _pair_count(db: AsyncSession, set_id: int) -> int:
    count = (await db.execute(
        select(func.count(MatchingPair.id)).where(MatchingPair.set_id == set_id)
    )).scalar()
    return int(count or 0)


async def _get_set_or_404(db: AsyncSession, set_id: int) -> MatchingSet:
    item = await db.get(MatchingSet, set_id)
    if not item:
        raise HTTPException(status_code=404, detail="关卡不存在")
    return item


async def _save_pairs(db: AsyncSession, set_id: int, pairs) -> None:
    await db.execute(delete(MatchingPair).where(MatchingPair.set_id == set_id))
    for index, pair in enumerate(pairs):
        db.add(MatchingPair(
            set_id=set_id,
            left_text=pair.left_text,
            right_text=pair.right_text,
            hint=pair.hint,
            order_index=index,
        ))


# --------------------------------------------------------------------------- 学生端

@router.get("/sets", summary="可玩的连连看关卡")
async def list_sets(
    page: int = 1,
    page_size: int = 12,
    category: str | None = None,
    keyword: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    page_size = min(MAX_PAGE_SIZE, max(1, page_size))

    conditions = [MatchingSet.is_active.is_(True)]
    if category and category in CATEGORY_LABELS:
        conditions.append(MatchingSet.category == category)
    if keyword and keyword.strip():
        like = "%%%s%%" % keyword.strip()
        conditions.append(or_(MatchingSet.title.like(like),
                              MatchingSet.description.like(like)))

    base = select(MatchingSet).where(*conditions)
    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    items = (await db.execute(
        base.order_by(MatchingSet.updated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    ids = [item.id for item in items]
    pair_counts, best_scores, my_plays = {}, {}, {}
    if ids:
        pair_counts = dict((await db.execute(
            select(MatchingPair.set_id, func.count(MatchingPair.id))
            .where(MatchingPair.set_id.in_(ids))
            .group_by(MatchingPair.set_id)
        )).all())
        best_scores = dict((await db.execute(
            select(MatchingRecord.set_id, func.max(MatchingRecord.score))
            .where(MatchingRecord.set_id.in_(ids),
                   MatchingRecord.user_id == current_user.id)
            .group_by(MatchingRecord.set_id)
        )).all())
        my_plays = dict((await db.execute(
            select(MatchingRecord.set_id, func.count(MatchingRecord.id))
            .where(MatchingRecord.set_id.in_(ids),
                   MatchingRecord.user_id == current_user.id)
            .group_by(MatchingRecord.set_id)
        )).all())

    result = []
    for item in items:
        payload = _set_payload(item, pair_count=int(pair_counts.get(item.id, 0)))
        payload["my_best"] = best_scores.get(item.id)
        payload["my_plays"] = int(my_plays.get(item.id, 0))
        result.append(payload)

    return {"items": result, "total": int(total), "page": page, "page_size": page_size}


@router.get("/sets/{set_id}", summary="关卡详情")
async def get_set(
    set_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_set_or_404(db, set_id)
    manager = _can_manage(current_user, item)
    if not item.is_active and not manager:
        raise HTTPException(status_code=404, detail="关卡不存在或已停用")

    pairs = (await db.execute(
        select(MatchingPair).where(MatchingPair.set_id == item.id)
        .order_by(MatchingPair.order_index, MatchingPair.id)
    )).scalars().all()

    my_best = (await db.execute(
        select(func.max(MatchingRecord.score))
        .where(MatchingRecord.set_id == item.id,
               MatchingRecord.user_id == current_user.id)
    )).scalar()
    my_plays = (await db.execute(
        select(func.count(MatchingRecord.id))
        .where(MatchingRecord.set_id == item.id,
               MatchingRecord.user_id == current_user.id)
    )).scalar() or 0

    payload = _set_payload(item, pair_count=len(pairs))
    payload.update({
        "pairs": [_pair_payload(p) for p in pairs],
        "can_edit": manager,
        "my_best": my_best,
        "my_plays": int(my_plays),
    })
    return payload


@router.post("/sets/{set_id}/records", summary="提交一局成绩")
async def submit_record(
    set_id: int,
    data: MatchingRecordIn,
    preview: bool = Query(False, description="试玩模式，不计入统计"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_set_or_404(db, set_id)
    if not item.is_active:
        raise HTTPException(status_code=400, detail="关卡已停用，无法提交成绩")

    actual_pairs = await _pair_count(db, set_id)
    if data.pairs_total != actual_pairs:
        raise HTTPException(status_code=400, detail="关卡内容已更新，请重新开始一局")

    if preview:
        return {"ok": True, "saved": False, "message": "试玩模式，未计入统计"}

    record = MatchingRecord(
        set_id=set_id,
        user_id=current_user.id,
        score=data.score,
        mistakes=data.mistakes,
        pairs_total=data.pairs_total,
        max_combo=data.max_combo,
        duration_seconds=data.duration_seconds,
    )
    db.add(record)
    item.play_count = (item.play_count or 0) + 1
    await db.commit()
    await db.refresh(record)

    best = (await db.execute(
        select(func.max(MatchingRecord.score)).where(
            MatchingRecord.set_id == set_id,
            MatchingRecord.user_id == current_user.id)
    )).scalar()

    return {"ok": True, "saved": True, "record_id": record.id,
            "my_best": best, "play_count": item.play_count}


@router.get("/sets/{set_id}/leaderboard", summary="关卡排行榜")
async def leaderboard(
    set_id: int,
    limit: int = Query(8, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_set_or_404(db, set_id)
    if not item.is_active and not _can_manage(current_user, item):
        raise HTTPException(status_code=404, detail="关卡不存在或已停用")

    rows = (await db.execute(
        select(MatchingRecord, User)
        .join(User, User.id == MatchingRecord.user_id)
        .where(MatchingRecord.set_id == set_id)
        .order_by(MatchingRecord.score.desc(),
                  MatchingRecord.duration_seconds.asc(),
                  MatchingRecord.created_at.asc())
        .limit(max(limit * 4, 20))
    )).all()

    # 每人只保留最好的一条，避免同一个人刷榜占满整个排行榜
    items = []
    seen_users = set()
    for record, user in rows:
        if user.id in seen_users:
            continue
        seen_users.add(user.id)
        items.append({
            "rank": len(items) + 1,
            "name": _display_name(user),
            "is_me": user.id == current_user.id,
            "score": record.score,
            "mistakes": record.mistakes,
            "duration_seconds": record.duration_seconds,
            "created_at": _iso(record.created_at),
        })
        if len(items) >= limit:
            break

    return {"items": items}


@router.get("/my/records", summary="我的连连看记录")
async def my_records(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    page_size = min(MAX_PAGE_SIZE, max(1, page_size))

    total = (await db.execute(
        select(func.count(MatchingRecord.id))
        .where(MatchingRecord.user_id == current_user.id)
    )).scalar() or 0

    rows = (await db.execute(
        select(MatchingRecord, MatchingSet)
        .join(MatchingSet, MatchingSet.id == MatchingRecord.set_id)
        .where(MatchingRecord.user_id == current_user.id)
        .order_by(MatchingRecord.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all()

    return {
        "items": [{
            "id": record.id,
            "set_id": record.set_id,
            "set_title": item.title,
            "category_label": CATEGORY_LABELS.get(item.category, item.category),
            "score": record.score,
            "mistakes": record.mistakes,
            "pairs_total": record.pairs_total,
            "duration_seconds": record.duration_seconds,
            "created_at": _iso(record.created_at),
        } for record, item in rows],
        "total": int(total), "page": page, "page_size": page_size,
    }


@router.get("/my/summary", summary="我的连连看汇总")
async def my_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(
            func.count(MatchingRecord.id),
            func.max(MatchingRecord.score),
            func.sum(MatchingRecord.duration_seconds),
        ).where(MatchingRecord.user_id == current_user.id)
    )).one()
    plays = int(row[0] or 0)
    return {
        "plays": plays,
        "best_score": int(row[1] or 0),
        "total_seconds": int(row[2] or 0),
    }


# --------------------------------------------------------------------------- 管理端

@router.get("/manage/sets", summary="我管理的关卡")
async def manage_sets(
    page: int = 1,
    page_size: int = 10,
    category: str | None = None,
    keyword: str | None = None,
    current_user: User = Depends(get_current_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    page_size = min(MAX_PAGE_SIZE, max(1, page_size))

    conditions = []
    if current_user.role != UserRole.ADMIN:
        conditions.append(MatchingSet.creator_id == current_user.id)
    if category and category in CATEGORY_LABELS:
        conditions.append(MatchingSet.category == category)
    if keyword and keyword.strip():
        like = "%%%s%%" % keyword.strip()
        conditions.append(or_(MatchingSet.title.like(like),
                              MatchingSet.description.like(like)))

    base = select(MatchingSet).where(*conditions)
    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    items = (await db.execute(
        base.order_by(MatchingSet.updated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    ids = [item.id for item in items]
    pair_counts = {}
    stats = {}
    if ids:
        pair_counts = dict((await db.execute(
            select(MatchingPair.set_id, func.count(MatchingPair.id))
            .where(MatchingPair.set_id.in_(ids))
            .group_by(MatchingPair.set_id)
        )).all())
        rows = (await db.execute(
            select(
                MatchingRecord.set_id,
                func.count(MatchingRecord.id),
                func.avg(MatchingRecord.score),
                func.avg(MatchingRecord.mistakes),
                func.avg(
                    1.0 * MatchingRecord.pairs_total
                    / (MatchingRecord.pairs_total + MatchingRecord.mistakes)
                ),
            ).where(MatchingRecord.set_id.in_(ids))
            .group_by(MatchingRecord.set_id)
        )).all()
        for set_id, count, avg_score, avg_mistakes, avg_accuracy in rows:
            stats[set_id] = {
                "record_count": int(count or 0),
                "avg_score": round(float(avg_score or 0), 1),
                "avg_mistakes": round(float(avg_mistakes or 0), 1),
                "avg_accuracy": round(float(avg_accuracy or 0) * 100, 1),
            }

    result = []
    for item in items:
        payload = _set_payload(item, pair_count=int(pair_counts.get(item.id, 0)))
        payload.update(stats.get(item.id, {
            "record_count": 0, "avg_score": 0, "avg_mistakes": 0, "avg_accuracy": 0,
        }))
        result.append(payload)

    return {"items": result, "total": int(total), "page": page, "page_size": page_size}


@router.post("/sets", summary="新建关卡", status_code=201)
async def create_set(
    data: MatchingSetIn,
    current_user: User = Depends(get_current_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    item = MatchingSet(
        title=data.title,
        description=data.description,
        category=data.category,
        difficulty=data.difficulty,
        grade=data.grade,
        is_active=data.is_active,
        creator_id=current_user.id,
    )
    db.add(item)
    await db.flush()
    await _save_pairs(db, item.id, data.pairs)
    await db.commit()
    await db.refresh(item)

    payload = _set_payload(item, pair_count=len(data.pairs))
    payload["pairs"] = [{
        "left_text": pair.left_text,
        "right_text": pair.right_text,
        "hint": pair.hint,
    } for pair in data.pairs]
    return payload


@router.put("/sets/{set_id}", summary="修改关卡")
async def update_set(
    set_id: int,
    data: MatchingSetIn,
    current_user: User = Depends(get_current_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_set_or_404(db, set_id)
    _ensure_manageable(current_user, item)

    item.title = data.title
    item.description = data.description
    item.category = data.category
    item.difficulty = data.difficulty
    item.grade = data.grade
    item.is_active = data.is_active
    await _save_pairs(db, item.id, data.pairs)
    await db.commit()
    await db.refresh(item)

    return {"ok": True, "id": item.id, "pair_count": len(data.pairs)}


@router.delete("/sets/{set_id}", summary="删除关卡")
async def delete_set(
    set_id: int,
    current_user: User = Depends(get_current_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_set_or_404(db, set_id)
    _ensure_manageable(current_user, item)

    await db.execute(delete(MatchingRecord).where(MatchingRecord.set_id == set_id))
    # 配对交给 ORM 的 cascade 删除，避免和批量 DELETE 重复
    await db.delete(item)
    await db.commit()
    return {"ok": True, "message": "已删除"}


@router.get("/manage/sets/{set_id}/records", summary="关卡作答记录")
async def set_records(
    set_id: int,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_set_or_404(db, set_id)
    _ensure_manageable(current_user, item)

    page = max(1, page)
    page_size = min(MAX_PAGE_SIZE, max(1, page_size))
    total = (await db.execute(
        select(func.count(MatchingRecord.id))
        .where(MatchingRecord.set_id == set_id)
    )).scalar() or 0

    rows = (await db.execute(
        select(MatchingRecord, User)
        .join(User, User.id == MatchingRecord.user_id)
        .where(MatchingRecord.set_id == set_id)
        .order_by(MatchingRecord.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all()

    return {
        "items": [{
            "id": record.id,
            "student_id": user.id,
            "student_name": _display_name(user),
            "username": user.username,
            "score": record.score,
            "mistakes": record.mistakes,
            "pairs_total": record.pairs_total,
            "accuracy": round(
                record.pairs_total / max(1, record.pairs_total + record.mistakes) * 100, 1),
            "duration_seconds": record.duration_seconds,
            "created_at": _iso(record.created_at),
        } for record, user in rows],
        "total": int(total), "page": page, "page_size": page_size,
    }


# --------------------------------------------------------------------------- 批量导入

@router.post("/import", summary="批量导入关卡（xlsx / csv / txt）")
async def import_set(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    category: str = Form("mixed"),
    difficulty: str = Form("medium"),
    grade: str = Form(""),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_teacher_or_admin),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()
    try:
        pairs, warnings = parse_file(file.filename or "", raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400,
                            detail="文件解析失败：%s" % str(exc)[:120])

    if category not in CATEGORY_LABELS:
        category = "mixed"
    if difficulty not in DIFFICULTY_LABELS:
        difficulty = "medium"

    fallback_title = (file.filename or "导入的关卡").rsplit(".", 1)[0]
    item = MatchingSet(
        title=(title.strip() or fallback_title)[:80],
        description=(description.strip() or None),
        category=category,
        difficulty=difficulty,
        grade=(grade.strip() or None),
        is_active=bool(is_active),
        creator_id=current_user.id,
    )
    db.add(item)
    await db.flush()
    for index, pair in enumerate(pairs):
        db.add(MatchingPair(
            set_id=item.id,
            left_text=pair["left_text"],
            right_text=pair["right_text"],
            hint=pair.get("hint"),
            order_index=index,
        ))
    await db.commit()
    await db.refresh(item)

    return {
        "ok": True,
        "id": item.id,
        "title": item.title,
        "pair_count": len(pairs),
        "warnings": warnings[:10],
        "passed": len(warnings),
    }


@router.get("/import/template", summary="下载导入模板")
async def import_template(
    current_user: User = Depends(get_current_teacher_or_admin),
):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "连连看"
    headers = ["左项（物质 / 官能团 / 方程式）", "右项（俗称 / 结构 / 现象）", "提示（可选，配对成功后显示）"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4F46E5")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    examples = [
        ["氢氧化钠", "烧碱、火碱、苛性钠", "NaOH 的俗名，强碱，有腐蚀性"],
        ["羧基（—COOH）", "羧酸类，具有酸性", "羧基中的 O—H 可以电离出 H⁺"],
        ["2Na + 2H₂O = 2NaOH + H₂↑", "钠浮在水面熔成小球并游动", "钠与水反应放热，生成氢气"],
        ["乙醇", "酒精", "C₂H₅OH，医用酒精的主要成分"],
    ]
    for row in examples:
        sheet.append(row)
    widths = [36, 32, 44]
    for index, width in enumerate(widths):
        sheet.column_dimensions[chr(ord("A") + index)].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=chemlearn-matching-template.xlsx"},
    )
