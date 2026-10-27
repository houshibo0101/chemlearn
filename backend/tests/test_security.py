"""
安全层测试
覆盖：JWT 签发/校验/过期/防篡改、密码哈希、生产配置防呆、注册→登录→鉴权全链路
（2026-10-10 随 PyJWT 迁移与 SECRET_KEY 防呆加固新增）
"""
import pytest
from datetime import timedelta


class TestJWT:
    """JWT 令牌单元测试（PyJWT 实现）"""

    def test_roundtrip_with_claims(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token("user:42", {"role": "student", "grade": "高二"})
        payload = decode_token(token)
        assert payload["sub"] == "user:42"
        assert payload["role"] == "student"
        assert payload["grade"] == "高二"
        assert "exp" in payload

    def test_tampered_token_rejected(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token("user:1")
        # 篡改签名部分
        head, body, sig = token.split(".")
        bad = f"{head}.{body}.AAAA{sig[4:]}"
        assert decode_token(bad) is None

    def test_garbage_token_rejected(self):
        from app.core.security import decode_token
        assert decode_token("not.a.token") is None
        assert decode_token("") is None

    def test_expired_token_rejected(self):
        import jwt as pyjwt
        from app.core.config import settings
        from app.core.security import decode_token
        expired = pyjwt.encode(
            {"sub": "user:1", "exp": datetime_utcnow() - timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        assert decode_token(expired) is None

    def test_wrong_key_rejected(self):
        import jwt as pyjwt
        from app.core.config import settings
        from app.core.security import decode_token
        forged = pyjwt.encode(
            {"sub": "user:1", "exp": datetime_utcnow() + timedelta(hours=1)},
            "attacker-key-not-ours",
            algorithm=settings.ALGORITHM,
        )
        assert decode_token(forged) is None


def datetime_utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_and_verify(self):
        from app.core.security import hash_password, verify_password
        h = hash_password("S3cure-Pass!")
        assert h != "S3cure-Pass!"
        assert verify_password("S3cure-Pass!", h) is True

    def test_wrong_password_fails(self):
        from app.core.security import hash_password, verify_password
        h = hash_password("correct-horse")
        assert verify_password("wrong-battery", h) is False

    def test_hash_is_salted(self):
        """同一密码两次哈希结果应不同（自动加盐）"""
        from app.core.security import hash_password
        assert hash_password("same-pass-1") != hash_password("same-pass-1")


class TestProductionConfigGuard:
    """生产模式配置防呆测试"""

    def _make_settings(self, **overrides):
        from app.core.config import Settings
        return Settings(_env_file=None, **overrides)

    def test_debug_mode_allows_defaults(self):
        s = self._make_settings(DEBUG=True)
        assert s.SECRET_KEY  # 开发模式不拦截

    def test_production_rejects_default_secret(self):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            self._make_settings(DEBUG=False)

    def test_production_rejects_default_admin_password(self):
        with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
            self._make_settings(
                DEBUG=False,
                SECRET_KEY="a-very-strong-random-secret-key-2026",
            )

    def test_production_accepts_custom_values(self):
        s = self._make_settings(
            DEBUG=False,
            SECRET_KEY="a-very-strong-random-secret-key-2026",
            ADMIN_PASSWORD="n0t-the-default",
        )
        assert s.DEBUG is False


class TestAuthFlow:
    """注册→登录→携带令牌访问受保护接口 全链路"""

    @pytest.mark.asyncio
    async def test_register_login_me(self, client):
        import random
        uname = f"pytest_sec_{random.randint(10000, 99999)}"
        password = "Passw0rd-secure"

        r = await client.post(
            "/api/v1/auth/register",
            json={"username": uname, "password": password, "full_name": "安全测试学生"},
        )
        assert r.status_code in [200, 201], r.text

        r = await client.post(
            "/api/v1/auth/login",
            json={"username": uname, "password": password},
        )
        assert r.status_code == 200, r.text
        token = r.json().get("access_token")
        assert token

        r = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["username"] == uname

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_fake_token(self, client):
        r = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fake.token.value"},
        )
        assert r.status_code in [401, 403]
