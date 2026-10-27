"""
ChemLearn AI 独立服务
单独运行，负责AI问答、对话历史、token统计
端口: 8001
主后端通过HTTP调用此服务，实现AI模块独立部署和扩容
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.services.ai_service import AIService
from app.schemas.ai import ChatMessage


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("[AI服务] 数据库初始化完成")
    print(f"[AI服务] AI模型: {settings.AI_MODEL}")
    print(f"[AI服务] 监听端口: 8001")
    yield


app = FastAPI(title="ChemLearn AI Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 请求模型 ==========

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    context: Optional[str] = None


class ChatWithHistoryRequest(BaseModel):
    user_id: int
    message: str
    context: Optional[str] = None


class ExplainWrongRequest(BaseModel):
    user_id: int
    question_title: str
    question_content: Optional[str] = None
    correct_answer: str
    analysis: Optional[str] = None
    user_answer: Optional[str] = None
    follow_up: Optional[str] = None


class HistoryRequest(BaseModel):
    user_id: int


# ========== 健康检查 ==========

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-service", "model": settings.AI_MODEL}


# ========== AI 对话接口 ==========

@app.post("/chat")
async def chat(req: ChatRequest):
    """纯AI对话，不保存历史"""
    if not settings.AI_API_KEY:
        return {"reply": "【AI服务未配置】请在.env中设置AI_API_KEY", "usage": {}}
    reply, usage = await AIService.chat(
        message=req.message,
        history=req.history,
        context=req.context,
    )
    return {"reply": reply, "usage": usage}


@app.post("/chat-with-history")
async def chat_with_history(req: ChatWithHistoryRequest):
    """带历史记录的AI对话，自动保存、配额管理、token统计"""
    async with AsyncSessionLocal() as db:
        reply = await AIService.chat_with_history(
            db=db,
            user_id=req.user_id,
            message=req.message,
            context=req.context,
        )
    return {"reply": reply}


@app.post("/explain-wrong")
async def explain_wrong(req: ExplainWrongRequest):
    """错题AI讲解"""
    async with AsyncSessionLocal() as db:
        reply = await AIService.explain_wrong_question(
            db=db,
            user_id=req.user_id,
            question_title=req.question_title,
            question_content=req.question_content,
            correct_answer=req.correct_answer,
            analysis=req.analysis,
            user_answer=req.user_answer,
            follow_up=req.follow_up,
        )
    return {"reply": reply}


# ========== 历史记录接口 ==========

@app.get("/history/{user_id}")
async def get_history(user_id: int):
    """获取用户对话历史"""
    async with AsyncSessionLocal() as db:
        items = await AIService.get_history_list(db, user_id)
        return [{"id": i.id, "role": i.role, "content": i.content, "created_at": i.created_at.isoformat() if i.created_at else None} for i in items]


@app.delete("/history/{user_id}")
async def clear_history(user_id: int):
    """清空用户对话历史"""
    async with AsyncSessionLocal() as db:
        count = await AIService.clear_history(db, user_id)
    return {"message": f"已清空 {count} 条", "count": count}


@app.get("/history/{user_id}/stats")
async def history_stats(user_id: int):
    """获取对话历史配额使用情况"""
    async with AsyncSessionLocal() as db:
        return await AIService.get_history_size(db, user_id)


@app.get("/usage/total")
async def total_usage():
    """系统总存储统计"""
    async with AsyncSessionLocal() as db:
        return await AIService.get_total_storage(db)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, workers=1)
