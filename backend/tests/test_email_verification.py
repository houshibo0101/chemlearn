# -*- coding: utf-8 -*-
"""注册邮箱验证码：必须验证、错误拒绝、验证码一次性"""
import time

import pytest
from httpx import AsyncClient

from app.core.config import settings

pytestmark = pytest.mark.asyncio


async def test_register_requires_email_code(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    monkeypatch.setattr(settings, "SMTP_DEBUG", True)

    stamp = int(time.time() * 1000)
    email = "code_%d@example.com" % stamp
    username = "codeuser%d" % (stamp % 100000000)

    resp = await client.post("/api/v1/auth/send-code", json={"email": email})
    assert resp.status_code == 200, resp.text
    code = resp.json().get("debug_code")
    assert code and len(code) == 6 and code.isdigit()

    payload = {
        "username": username,
        "password": "Test123456",
        "email": email,
        "full_name": "验证码测试",
    }

    # 不填验证码
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "验证码" in resp.json()["detail"]

    # 错误验证码
    wrong = "000001" if code != "000001" else "000002"
    resp = await client.post("/api/v1/auth/register", json={**payload, "code": wrong})
    assert resp.status_code == 400
    assert "验证码" in resp.json()["detail"]

    # 正确验证码
    resp = await client.post("/api/v1/auth/register", json={**payload, "code": code})
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["email"] == email

    # 验证码只能用一次
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username + "b",
            "password": "Test123456",
            "email": "other_%d@example.com" % stamp,
            "code": code,
            "full_name": "验证码重复测试",
        },
    )
    assert resp.status_code == 400
