# 单元测试使用说明

## 安装测试依赖
```bash
cd ~/chemlearn/backend
venv/bin/pip install pytest pytest-asyncio httpx psutil
```

## 运行测试
```bash
# 运行所有测试
venv/bin/pytest

# 运行指定测试文件
venv/bin/pytest tests/test_core.py

# 运行指定测试类
venv/bin/pytest tests/test_core.py::TestAuth

# 运行指定测试方法
venv/bin/pytest tests/test_core.py::TestAuth::test_login_wrong_password

# 显示详细输出
venv/bin/pytest -v

# 生成测试报告
venv/bin/pytest --tb=long
```

## 测试覆盖范围
- ✅ 健康检查接口
- ✅ 认证接口（登录、注册、密码强度）
- ✅ 题目接口（权限检查、公开接口）
- ✅ 密码强度校验工具
- ✅ 缓存服务

## 注意事项
1. 测试会连接真实数据库，建议在测试环境运行
2. 认证测试依赖预置的admin账号
3. 异步测试需要pytest-asyncio插件
4. 每次修改核心代码后建议跑一遍测试
