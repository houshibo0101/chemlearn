"""
管理员 - 题目批量导入（图片/PDF → OCR/AI识别 → 结构化 → 入库）
"""
import base64
import json
import io
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, Question
from app.core.config import settings
from app.services.cache_service import cache

router = APIRouter(prefix="/admin/questions", tags=["管理员-题目导入"])


# ============ AI 识别相关 ============

async def ai_vision_recognize(image_b64: str, filename: str) -> str:
    """用AI视觉模型识别图片中的题目内容"""
    import httpx

    # 优先使用视觉模型，没有则用普通模型
    model = getattr(settings, 'AI_VISION_MODEL', None) or settings.AI_MODEL

    messages = [
        {
            "role": "system",
            "content": "你是一个化学题目识别专家。请仔细识别图片中的化学题目，完整输出题目内容，包括题干、选项、答案、解析等。保持原始格式，不要遗漏任何信息。"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                },
                {
                    "type": "text",
                    "text": "请完整识别这张图片中的化学题目内容，包括所有文字、公式、选项。"
                }
            ]
        }
    ]

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.AI_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        # 视觉模型不支持时，降级为提示需要OCR
        raise HTTPException(status_code=500, detail=f"AI视觉识别失败: {str(e)}")


async def ai_structure_questions(raw_text: str) -> list:
    """用AI把原始文本结构化成题目列表"""
    import httpx

    prompt = f"""请将以下化学题目文本结构化为JSON数组。每道题包含以下字段：
- title: 题目标题/题干（必填）
- content: 题目详细内容（可选，题干较长时放这里）
- question_type: 题目类型，只能是 single(单选)/multiple(多选)/fill(填空)/calculation(计算)
- difficulty: 难度，只能是 easy/medium/hard
- grade: 适用学段，如 高一/高二/高三
- knowledge_point: 知识点
- options: 选项数组，每个元素 {{"key":"A","text":"选项内容"}}，选择题必填，填空/计算题填[]
- answer: 正确答案（必填，选择题填字母如"A"，填空题填答案）
- analysis: 解析（可选）

要求：
1. 仔细识别每一道题，不要遗漏
2. 化学方程式、公式要完整保留
3. 如果文本中没有明确答案，answer填"待补充"，analysis填"暂无解析"
4. 只输出JSON数组，不要输出其他文字

原始文本：
{raw_text[:8000]}"""

    messages = [
        {"role": "system", "content": "你是一个化学题目结构化专家，只输出JSON。"},
        {"role": "user", "content": prompt}
    ]

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.AI_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                json={
                    "model": settings.AI_MODEL,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # 解析JSON
            result = json.loads(content)
            # 兼容返回 {"questions": [...]} 或直接数组
            if isinstance(result, dict) and "questions" in result:
                return result["questions"]
            if isinstance(result, list):
                return result
            return [result] if result else []
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI返回JSON解析失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI结构化失败: {str(e)}")


def extract_pdf_text(file_content: bytes) -> str:
    """从PDF提取文字"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except ImportError:
        raise HTTPException(status_code=500, detail="未安装PyPDF2，请执行: pip install PyPDF2")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF解析失败: {str(e)}")


# ============ 接口 ============

@router.post("/import/preview", summary="【管理员】上传文件并预览识别结果")
async def import_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传图片或PDF，返回AI识别结构化后的题目列表（不入库，供预览确认）"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    content = await file.read()

    print(f"[题目导入] 收到文件: {file.filename}, 大小: {len(content)} bytes, 类型: {ext}")

    # 1. 提取原始文本
    raw_text = ""
    if ext in ["jpg", "jpeg", "png", "bmp", "webp"]:
        # 图片：AI视觉识别
        if not settings.AI_API_KEY:
            raise HTTPException(status_code=500, detail="AI服务未配置，无法识别图片")
        image_b64 = base64.b64encode(content).decode()
        raw_text = await ai_vision_recognize(image_b64, file.filename)
        print(f"[题目导入] 图片识别完成，长度: {len(raw_text)}")
    elif ext == "pdf":
        # PDF：提取文字
        raw_text = extract_pdf_text(content)
        print(f"[题目导入] PDF提取完成，长度: {len(raw_text)}")
        if not raw_text or len(raw_text) < 10:
            # PDF文字提取失败，提示可能是扫描件
            raise HTTPException(
                status_code=400,
                detail="PDF未提取到文字，可能是扫描件（图片型PDF）。解决方法：1) 用WPS/Adobe打开PDF导出为图片；2) 手机截图后上传图片；3) 使用OCR工具将PDF转为可复制文字后再上传。"
            )
    elif ext in ["txt", "md"]:
        raw_text = content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}，支持 jpg/jpeg/png/pdf/txt/md")

    if not raw_text or len(raw_text) < 5:
        raise HTTPException(status_code=400, detail="未识别到有效内容")

    # 2. AI结构化
    questions = await ai_structure_questions(raw_text)
    print(f"[题目导入] 结构化完成，共 {len(questions)} 道题")

    # 3. 返回预览
    return {
        "filename": file.filename,
        "raw_text_preview": raw_text[:500],
        "question_count": len(questions),
        "questions": questions,
    }


@router.post("/import/confirm", summary="【管理员】确认导入题目")
async def import_confirm(
    questions: list = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认导入题目，批量入库"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    # 解析questions（前端传JSON字符串）
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except:
            raise HTTPException(status_code=400, detail="questions格式错误")

    if not questions:
        raise HTTPException(status_code=400, detail="没有要导入的题目")

    # 获取当前最大编号
    max_code = (await db.execute(
        select(func.max(Question.question_code))
    )).scalar()
    next_num = 1
    if max_code:
        match = re.search(r'(\d+)', max_code)
        if match:
            next_num = int(match.group(1)) + 1

    imported = 0
    failed = 0
    results = []

    for q in questions:
        try:
            # 处理选项
            options = q.get("options", [])
            if isinstance(options, str):
                options = json.loads(options)

            # 生成编号
            code = f"Q{next_num:04d}"
            next_num += 1

            question = Question(
                question_code=code,
                title=q.get("title", "未命名题目")[:500],
                content=q.get("content", ""),
                question_type=q.get("question_type", "single"),
                difficulty=q.get("difficulty", "medium"),
                grade=q.get("grade", ""),
                knowledge_point=q.get("knowledge_point", ""),
                options=json.dumps(options, ensure_ascii=False) if options else None,
                answer=q.get("answer", "待补充"),
                analysis=q.get("analysis", ""),
                creator_id=current_user.id,
            )
            db.add(question)
            imported += 1
            results.append({"code": code, "title": question.title[:50], "status": "success"})
        except Exception as e:
            failed += 1
            results.append({"title": q.get("title", "未知")[:50], "status": "failed", "error": str(e)})

    await db.commit()

    # 清除题目缓存
    cache.delete_pattern("q:list:*")
    cache.delete_pattern("q:detail:*")

    return {
        "imported": imported,
        "failed": failed,
        "total": len(questions),
        "results": results,
    }
