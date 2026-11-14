# -*- coding: utf-8 -*-
"""管理员 AI 接口配置：脱敏读取、更新、写回 .env"""
import time

import pytest
from httpx import AsyncClient

from app.api import admin_dashboard
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import User, UserRole


@pytest.mark.asyncio
async def test_ai_config_update(client: AsyncClient, monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DEBUG=true\nSECRET_KEY=keep-me\nAI_API_BASE=https://old.example/v1\nAI_API_KEY=old-secret-key\n", encoding="utf-8")
    monkeypatch.setattr(admin_dashboard, "_ENV_PATH", env_file)
    monkeypatch.setattr(settings, "AI_API_BASE", "https://old.example/v1")
    monkeypatch.setattr(settings, "AI_API_KEY", "old-secret-key")
    monkeypatch.setattr(settings, "AI_MODEL", "old-model")

    username = "aiadmin%d" % int(time.time() * 1000)
    async with AsyncSessionLocal() as session:
        session.add(User(
            username=username,
            hashed_password=hash_password("Test123456"),
            role=UserRole.ADMIN,
            is_active=True,
        ))
        await session.commit()

    login = await client.post("/api/v1/auth/login", json={"username": username, "password": "Test123456"})
    assert login.status_code == 200, login.text
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}

    r = await client.get("/api/v1/admin/dashboard/ai-config", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["api_base"] == "https://old.example/v1"
    assert data["key_configured"] is True
    assert data["key_hint"].startswith("old-") and "old-secret-key" not in data["key_hint"]

    r = await client.put(
        "/api/v1/admin/dashboard/ai-config",
        headers=headers,
        json={"api_base": "https://new.example/v1/", "api_key": "sk-new-key-123456", "model": "new-model"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["api_base"] == "https://new.example/v1"
    assert data["model"] == "new-model"
    assert data["key_configured"] is True
    assert data["key_hint"].endswith("3456")

    saved = env_file.read_text(encoding="utf-8")
    assert "AI_API_BASE=https://new.example/v1" in saved
    assert "AI_API_KEY=sk-new-key-123456" in saved
    assert "AI_MODEL=new-model" in saved
    assert "SECRET_KEY=keep-me" in saved
    assert settings.AI_API_KEY == "sk-new-key-123456"

    # 留空 Key 时保留原值
    r = await client.put(
        "/api/v1/admin/dashboard/ai-config",
        headers=headers,
        json={"api_base": "https://new.example/v1", "api_key": "", "model": "new-model"},
    )
    assert r.status_code == 200
    assert "sk-new-key-123456" in env_file.read_text(encoding="utf-8")

    # 清除 Key
    r = await client.put(
        "/api/v1/admin/dashboard/ai-config",
        headers=headers,
        json={"api_base": "https://new.example/v1", "clear_key": True},
    )
    assert r.status_code == 200
    assert r.json()["key_configured"] is False
    assert "AI_API_KEY=" not in env_file.read_text(encoding="utf-8")

    # 非法地址拒绝
    r = await client.put(
        "/api/v1/admin/dashboard/ai-config",
        headers=headers,
        json={"api_base": "not-a-url"},
    )
    assert r.status_code == 400
