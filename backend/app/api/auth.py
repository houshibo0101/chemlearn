"""
认证路由：注册、登录
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models import User, UserRole
from app.schemas import UserRegister, UserLogin, UserOut, Token, UserUpdate, ChangePassword, SendCodeRequest, APIRegisterRequest, ResetPasswordRequest
from app.services.verification import generate_code, verify_code
from app.services.email_service import send_verification_code
from app.services.rate_limiter import rate_limiter, check_login_failure, record_login_failure, reset_login_failure
from app.services.password_validator import validate_password_strength

router = APIRouter(prefix="/auth", tags=["认证"])


def get_client_ip(request: Request) -> str:
    """获取真实客户端IP，优先从X-Forwarded-For获取（支持反向代理/内网穿透）"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


@router.post("/password-strength", summary="检查密码强度")
async def check_password_strength(data: dict):
    """检查密码强度，返回评分和建议"""
    from app.services.password_validator import get_password_strength
    password = data.get("password", "")
    return get_password_strength(password)


@router.post("/send-code", summary="发送邮箱验证码")
async def send_code(data: SendCodeRequest, request: Request):
    """发送6位数字验证码到邮箱，有效期10分钟
    限流：同一邮箱1分钟最多1次，每天最多5次
    """
    email = data.email.strip()
    if not email or '@' not in email:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # 频率限制：1分钟1次
    if not rate_limiter.allow(f"code_min_{email}", 1, 60):
        raise HTTPException(status_code=429, detail="验证码发送过于频繁，请1分钟后再试")

    # 频率限制：每天5次
    if not rate_limiter.allow(f"code_day_{email}", 5, 86400):
        raise HTTPException(status_code=429, detail="该邮箱今日验证码已达上限（5次）")

    code = generate_code(email)
    success = send_verification_code(email, code)

    if success:
        return {"message": "验证码已发送，请查收邮箱", "debug": None}
    else:
        # SMTP未配置时，返回验证码用于调试（生产环境应移除）
        return {"message": "验证码已生成（SMTP未配置，调试模式）", "debug_code": code}


@router.post("/api-register", response_model=Token, summary="API平台注册（邮箱验证）")
async def api_register(data: APIRegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """API开放平台注册，必须验证邮箱验证码
    限流：同一IP每天最多注册3个账号
    """
    client_ip = get_client_ip(request)

    # IP限流：每天50个（内网穿透场景下多个用户共享出口IP）
    if not rate_limiter.allow(f"register_ip_{client_ip}", 50, 86400):
        raise HTTPException(status_code=429, detail="该IP今日注册已达上限（50个）")

    # 密码强度校验
    valid, msg = validate_password_strength(data.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # 验证邮箱验证码
    if not verify_code(data.email.strip(), data.verification_code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 检查用户名
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        grade=data.grade,
        role=UserRole.STUDENT,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), {"role": user.role.value})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=Token, summary="用户注册")
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    """用户注册
    限流：同一IP每天最多注册3个账号
    """
    client_ip = get_client_ip(request)

    # IP限流：每天50个（内网穿透场景下多个用户共享出口IP）
    if not rate_limiter.allow(f"register_ip_{client_ip}", 50, 86400):
        raise HTTPException(status_code=429, detail="该IP今日注册已达上限（50个）")

    # 密码强度校验
    valid, msg = validate_password_strength(data.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # 检查用户名
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 空字符串邮箱转None，避免UNIQUE约束冲突
    email = data.email.strip() if data.email and data.email.strip() else None
    if email:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(
        username=data.username,
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        grade=data.grade,
        role=UserRole.STUDENT,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), {"role": user.role.value})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token, summary="用户登录")
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """用户登录
    限流：同一IP+用户名5分钟内最多5次失败，超过锁定15分钟
    """
    client_ip = get_client_ip(request)

    # 检查登录失败次数
    allowed, remaining = check_login_failure(client_ip, data.username)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"登录失败次数过多，请{remaining}秒后再试")

    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        # 记录失败
        record_login_failure(client_ip, data.username)
        raise HTTPException(status_code=401, detail=f"用户名或密码错误，剩余尝试次数：{remaining - 1}")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 登录成功，重置失败计数
    reset_login_failure(client_ip, data.username)

    token = create_access_token(str(user.id), {"role": user.role.value})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/send-reset-code", summary="发送重置密码验证码")
async def send_reset_code(data: SendCodeRequest, request: Request):
    """发送重置密码验证码到邮箱
    限流：同一邮箱1分钟最多1次，每天最多5次
    """
    email = data.email.strip()
    if not email or '@' not in email:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # 频率限制
    if not rate_limiter.allow(f"reset_min_{email}", 1, 60):
        raise HTTPException(status_code=429, detail="验证码发送过于频繁，请1分钟后再试")
    if not rate_limiter.allow(f"reset_day_{email}", 5, 86400):
        raise HTTPException(status_code=429, detail="该邮箱今日验证码已达上限（5次）")

    code = generate_code(email)
    success = send_verification_code(email, code)

    if success:
        return {"message": "重置密码验证码已发送，请查收邮箱"}
    else:
        return {"message": "验证码已生成（SMTP未配置，调试模式）", "debug_code": code}


@router.post("/reset-password", summary="重置密码")
async def reset_password(data: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """通过邮箱验证码重置密码"""
    email = data.email.strip()

    # 验证验证码
    if not verify_code(email, data.verification_code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 密码强度校验
    valid, msg = validate_password_strength(data.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # 查找用户
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱未注册")

    # 更新密码
    user.hashed_password = hash_password(data.new_password)
    user.must_change_password = False
    await db.commit()

    return {"message": "密码重置成功，请用新密码登录"}


@router.get("/me", response_model=UserOut, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.put("/me", response_model=UserOut, summary="更新个人信息")
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.grade is not None:
        current_user.grade = data.grade
    if data.email is not None and data.email != current_user.email:
        # 检查邮箱是否被其他用户占用
        existing = (await db.execute(
            select(User).where(User.email == data.email, User.id != current_user.id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="该邮箱已被其他账号使用")
        current_user.email = data.email
    if data.password is not None:
        current_user.hashed_password = hash_password(data.password)
    await db.commit()
    await db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.post("/change-password", summary="修改密码")
async def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    current_user.hashed_password = hash_password(data.new_password)
    current_user.must_change_password = False
    await db.commit()
    return {"message": "密码修改成功"}
