"""
密码强度校验工具
"""
import re


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    校验密码强度
    返回: (是否通过, 错误信息)
    规则：
    - 至少6位
    - 包含字母和数字
    - 不能是纯数字或纯字母
    """
    if not password or len(password) < 6:
        return False, "密码长度至少6位"

    if len(password) > 64:
        return False, "密码长度不能超过64位"

    # 检查是否包含字母
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    # 检查是否包含数字
    has_digit = bool(re.search(r'[0-9]', password))

    if not has_letter:
        return False, "密码必须包含字母"

    if not has_digit:
        return False, "密码必须包含数字"

    # 检查常见弱密码
    weak_passwords = [
        '123456', 'password', '12345678', 'qwerty', 'abc123',
        '111111', '123123', 'admin123', 'password123', 'iloveyou',
    ]
    if password.lower() in weak_passwords:
        return False, "密码过于简单，请使用更复杂的密码"

    return True, ""


def get_password_strength(password: str) -> dict:
    """
    获取密码强度评分
    返回: {score: 0-4, level: '弱'/'中'/'强'/'很强', tips: [...]}
    """
    score = 0
    tips = []

    if len(password) >= 6:
        score += 1
    else:
        tips.append("密码长度至少6位")

    if len(password) >= 10:
        score += 1

    if bool(re.search(r'[a-z]', password)) and bool(re.search(r'[A-Z]', password)):
        score += 1
        tips.append("包含大小写字母")
    else:
        tips.append("建议包含大小写字母")

    if bool(re.search(r'[0-9]', password)):
        score += 1
    else:
        tips.append("建议包含数字")

    if bool(re.search(r'[^a-zA-Z0-9]', password)):
        score += 1
        tips.append("包含特殊字符")
    else:
        tips.append("建议包含特殊字符(!@#$%等)")

    if score <= 1:
        level = "弱"
    elif score <= 2:
        level = "中"
    elif score <= 3:
        level = "强"
    else:
        level = "很强"

    return {
        "score": min(score, 4),
        "level": level,
        "tips": tips,
    }
