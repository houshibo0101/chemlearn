"""
邮箱验证码管理
"""
import secrets
import time
from typing import Dict

# 内存存储验证码: {email: {"code": "123456", "expires": timestamp}}
_verification_codes: Dict[str, dict] = {}


def generate_code(email: str) -> str:
    """生成6位数字验证码"""
    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    _verification_codes[email] = {
        "code": code,
        "expires": time.time() + 600  # 10分钟有效
    }
    return code


def verify_code(email: str, code: str) -> bool:
    """验证验证码"""
    record = _verification_codes.get(email)
    if not record:
        return False
    if time.time() > record["expires"]:
        del _verification_codes[email]
        return False
    if record["code"] == code:
        del _verification_codes[email]  # 验证成功后删除
        return True
    return False


def cleanup_expired():
    """清理过期验证码"""
    now = time.time()
    expired = [email for email, record in _verification_codes.items() if now > record["expires"]]
    for email in expired:
        del _verification_codes[email]
