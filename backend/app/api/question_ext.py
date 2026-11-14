"""
题目图片上传 + 简答题批改
"""
import os
import io
import json
import logging
import uuid
import zipfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_teacher_or_admin
from app.models.user import User
from app.models.question import Question
from app.core.config import settings
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["题目扩展"])

# 上传根目录：默认 backend/uploads；本地部署器可通过 UPLOAD_DIR 指向自定义目录。
# 题目图片统一放在其下的 questions/ 子目录。
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_UPLOAD_ROOT = os.environ.get("UPLOAD_DIR") or os.path.join(_BACKEND_DIR, "uploads")
UPLOAD_DIR = os.path.join(_UPLOAD_ROOT, "questions")
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except OSError as exc:  # 目录不可写时不要让整个应用起不来
    logger.warning("题目图片上传目录不可用（%s）：%s", UPLOAD_DIR, exc)


@router.post("/upload-image", summary="上传题目图片")
async def upload_question_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传题目图片，返回访问URL"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {"url": f"/uploads/questions/{filename}", "filename": filename}


# --- KingDraw .kdx 导入 -----------------------------------------------------
# .kdx 本质是 zip：protocol 里是 JSON（原子/键 + 坐标），media 里是预览图。
# 优先把 protocol 转成 MOL 交给 Ketcher 高清重绘；解析不了再退回内嵌 PNG。
KDX_ELEMENTS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al",
    "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
    "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm",
    "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W",
    "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac", "Th", "Pa", "U",
}


def _kdx_doc_to_mol(doc):
    """把 KingDraw protocol 文档转成 MOL V2000；复杂基团/不支持时返回 None。"""
    elements = doc.get("elements") or []
    if not isinstance(elements, list):
        return None

    atoms = []
    bonds = []
    seen = set()
    for group in elements:
        for sub in group.get("subs") or []:
            kind = sub.get("id")
            prop = sub.get("prop") or {}
            kid = sub.get("kid") or sub.get("id")
            if kind == "node":
                if kid in seen:
                    continue
                symbol = (prop.get("type") or "").strip()
                # 带 label/html 的缩写基团（如 COOH、Ph）不硬转，交给 PNG 兜底
                if prop.get("label") or prop.get("html"):
                    return None
                if symbol not in KDX_ELEMENTS:
                    return None
                point = prop.get("point") or {}
                try:
                    x = float(point.get("x", 0)) * 12.0
                    y = -float(point.get("y", 0)) * 12.0
                except (TypeError, ValueError):
                    return None
                try:
                    charge = int(prop.get("charge") or 0)
                except (TypeError, ValueError):
                    charge = 0
                charge_code = {0: 0, 1: 3, 2: 2, 3: 1, -1: 5, -2: 6, -3: 7}.get(charge, 0)
                seen.add(kid)
                atoms.append({"kid": kid, "symbol": symbol, "x": x, "y": y, "charge": charge_code})
            elif kind == "bond":
                rels = sub.get("rels") or []
                if len(rels) != 2:
                    return None
                bond_type = int(prop.get("type") or 1)
                if bond_type not in (1, 2, 3, 4):
                    return None
                bonds.append({"rels": (rels[0], rels[1]), "type": bond_type})

    if not atoms or not bonds:
        return None
    index = {atom["kid"]: i + 1 for i, atom in enumerate(atoms)}
    lines = ["KingDraw import", "  ChemLearn", "",
             f"{len(atoms):3d}{len(bonds):3d}  0  0  0  0            999 V2000"]
    for atom in atoms:
        lines.append(
            f"{atom['x']:10.4f}{atom['y']:10.4f}{0.0:10.4f} {atom['symbol']:<3s}"
            f" 0{atom['charge']:3d}  0  0  0  0  0  0  0  0  0"
        )
    for bond in bonds:
        a = index.get(bond["rels"][0])
        b = index.get(bond["rels"][1])
        if not a or not b:
            return None
        lines.append(f"{a:3d}{b:3d}{bond['type']:3d}  0  0  0  0")
    return "\n".join(lines) + "\n"


@router.post("/import-kingdraw", summary="导入 KingDraw .kdx 文件")
async def import_kingdraw(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_teacher_or_admin),
):
    """解析 .kdx：返回 MOL（可编辑）或内嵌预览图 URL（兜底）。"""
    if not (file.filename or "").lower().endswith(".kdx"):
        raise HTTPException(status_code=400, detail="目前支持 KingDraw 的 .kdx 文件")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件不能超过 10MB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="不是有效的 .kdx 文件")

    names = set(archive.namelist())
    mol = None
    if "protocol" in names:
        try:
            raw = json.loads(archive.read("protocol").decode("utf-8", "replace"))
            doc = json.loads(raw["protocol"]) if isinstance(raw.get("protocol"), str) else raw
            mol = _kdx_doc_to_mol(doc)
        except Exception as exc:  # 解析失败就走 PNG 兜底
            logger.info("KingDraw protocol 解析失败：%s", exc)

    preview_url = None
    # 只有 MOL 解析失败时才落盘内嵌小图，避免每次导入都产生无用文件
    if not mol:
        for member in ("media/p_png.png", "media/p_jpg.jpg", "media/p_thumbnail.png"):
            if member in names:
                data = archive.read(member)
                ext = os.path.splitext(member)[1] or ".png"
                filename = f"{uuid.uuid4().hex}{ext}"
                with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
                    f.write(data)
                preview_url = f"/uploads/questions/{filename}"
                break

    if not mol and not preview_url:
        raise HTTPException(status_code=400, detail="未找到可用的结构数据或预览图")
    return {"mol": mol, "preview_url": preview_url, "source": "kingdraw"}


@router.post("/{question_id}/grade-subjective", summary="批改简答题")
async def grade_subjective(
    question_id: int,
    user_answer: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    简答题批改：先关键词匹配，命中率低于60%则调AI复批
    """
    question = (await db.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    keywords = []
    if question.keywords:
        try:
            keywords = json.loads(question.keywords)
        except:
            pass

    # 关键词匹配
    total_score = sum(kw.get("score", 1) for kw in keywords) if keywords else 10
    got_score = 0
    hit_keywords = []
    for kw in keywords:
        word = kw.get("word", "")
        score = kw.get("score", 1)
        if word and word in user_answer:
            got_score += score
            hit_keywords.append(word)

    hit_rate = got_score / total_score if total_score > 0 else 0
    result = {
        "question_id": question_id,
        "user_answer": user_answer,
        "keyword_score": got_score,
        "total_score": total_score,
        "hit_rate": round(hit_rate, 2),
        "hit_keywords": hit_keywords,
        "method": "keyword",
        "ai_comment": None,
        "final_score": got_score,
    }

    # 命中率低于60%，调AI复批
    if hit_rate < 0.6 and question.answer:
        try:
            ai_result = await _ai_grade(question, user_answer, total_score)
            if ai_result:
                result["method"] = "ai"
                result["ai_comment"] = ai_result.get("comment")
                result["final_score"] = ai_result.get("score", got_score)
        except Exception as e:
            # AI失败则用关键词结果
            pass

    return result


async def _ai_grade(question: Question, user_answer: str, total_score: int) -> dict:
    """调用AI批改简答题"""
    ai_url = getattr(settings, "AI_SERVICE_URL", "http://127.0.0.1:8001")
    prompt = f"""你是化学老师，请批改学生的简答题答案。

题目：{question.title}
{question.content or ''}

参考答案：{question.answer}

学生答案：{user_answer}

请按JSON格式返回：
{{"score": 得分(0-{total_score}), "comment": "评语，指出对在哪里错在哪里"}}

只返回JSON，不要其他内容。"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{ai_url}/v1/chat/completions", json={
            "model": "deepseek-v4-flash-260425",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        })
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # 提取JSON
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    return None
