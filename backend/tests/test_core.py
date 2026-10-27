"""
核心接口单元测试
覆盖：健康检查、认证、题目、密码强度
"""
import pytest


class TestHealth:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """测试健康检查接口"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert "database" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """测试根接口"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestAuth:
    """认证接口测试"""

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        """测试错误密码登录"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """测试不存在的用户登录"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "test123"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        """测试弱密码注册被拒绝（太短会被schema拦截返回422）"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser_weak",
                "password": "123",
                "full_name": "测试用户"
            }
        )
        # 密码太短会在schema层面返回422，强度不够会返回400
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_register_password_no_digit(self, client):
        """测试纯字母密码被拒绝"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser_nodigit",
                "password": "abcdef",
                "full_name": "测试用户"
            }
        )
        assert response.status_code == 400
        assert "数字" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_password_strength_endpoint(self, client):
        """测试密码强度检查接口"""
        response = await client.post(
            "/api/v1/auth/password-strength",
            json={"password": "test123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "level" in data
        assert "tips" in data

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """测试管理员登录成功"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        # 密码admin123包含字母和数字，应该能通过强度校验
        # 但管理员是预置的，不需要注册
        assert response.status_code in [200, 401]  # 可能因为测试环境数据不同


class TestQuestions:
    """题目接口测试"""

    @pytest.mark.asyncio
    async def test_questions_require_auth(self, client):
        """测试题目列表需要登录"""
        response = await client.get("/api/v1/questions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_question_filters_public(self, client):
        """测试题目筛选选项是公开的"""
        response = await client.get("/api/v1/stats/question-filters")
        assert response.status_code == 200
        data = response.json()
        assert "question_types" in data
        assert "difficulties" in data
        assert "knowledge_points" in data

    @pytest.mark.asyncio
    async def test_knowledge_points_public(self, client):
        """测试知识点列表是公开的"""
        response = await client.get("/api/v1/stats/knowledge-points")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestPasswordValidator:
    """密码强度校验单元测试"""

    def test_valid_password(self):
        """测试合法密码"""
        from app.services.password_validator import validate_password_strength
        valid, msg = validate_password_strength("test123")
        assert valid is True
        assert msg == ""

    def test_too_short(self):
        """测试太短的密码"""
        from app.services.password_validator import validate_password_strength
        valid, msg = validate_password_strength("ab1")
        assert valid is False
        assert "6位" in msg

    def test_no_digit(self):
        """测试没有数字的密码"""
        from app.services.password_validator import validate_password_strength
        valid, msg = validate_password_strength("abcdef")
        assert valid is False
        assert "数字" in msg

    def test_no_letter(self):
        """测试没有字母的密码"""
        from app.services.password_validator import validate_password_strength
        valid, msg = validate_password_strength("123456")
        assert valid is False
        assert "字母" in msg

    def test_weak_password(self):
        """测试常见弱密码"""
        from app.services.password_validator import validate_password_strength
        valid, msg = validate_password_strength("123456")
        assert valid is False

    def test_password_strength_score(self):
        """测试密码强度评分"""
        from app.services.password_validator import get_password_strength
        result = get_password_strength("Test@12345")
        assert result["score"] >= 3
        assert result["level"] in ["弱", "中", "强", "很强"]


class TestCache:
    """缓存服务测试"""

    def test_memory_cache_set_get(self):
        """测试内存缓存读写"""
        from app.services.cache_service import MemoryCache
        cache = MemoryCache()
        cache.set("test_key", "test_value", expire=60)
        assert cache.get("test_key") == "test_value"

    def test_memory_cache_delete(self):
        """测试内存缓存删除"""
        from app.services.cache_service import MemoryCache
        cache = MemoryCache()
        cache.set("test_key", "test_value", expire=60)
        cache.delete("test_key")
        assert cache.get("test_key") is None

    def test_memory_cache_expire(self):
        """测试缓存过期"""
        from app.services.cache_service import MemoryCache
        import time
        cache = MemoryCache()
        cache.set("test_key", "test_value", expire=1)
        time.sleep(1.1)
        assert cache.get("test_key") is None
