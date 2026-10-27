"""
邮件发送服务
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """发送HTML邮件"""
    if not settings.SMTP_HOST:
        print(f"[邮件] SMTP未配置，跳过发送。目标: {to_email}, 主题: {subject}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[邮件] 发送成功: {to_email}")
        return True
    except Exception as e:
        print(f"[邮件] 发送失败: {e}")
        return False


def send_verification_code(to_email: str, code: str) -> bool:
    """发送验证码邮件"""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
            <h2 style="color: #fff; margin: 0; font-size: 24px;">⚗️ ChemLearn API</h2>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0;">邮箱验证码</p>
        </div>
        <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px;">
            <p style="color: #333; font-size: 15px; line-height: 1.6;">您好，</p>
            <p style="color: #333; font-size: 15px; line-height: 1.6;">您正在注册 ChemLearn API 开放平台，验证码为：</p>
            <div style="text-align: center; margin: 24px 0;">
                <span style="display: inline-block; font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 8px; background: #fff; padding: 12px 32px; border-radius: 8px; border: 2px solid #667eea;">{code}</span>
            </div>
            <p style="color: #666; font-size: 13px; line-height: 1.6;">验证码有效期为 10 分钟，请勿泄露给他人。</p>
            <p style="color: #999; font-size: 12px; margin-top: 20px;">如非本人操作，请忽略此邮件。</p>
        </div>
        <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
            © 2026 ChemLearn API 开放平台
        </div>
    </div>
    """
    return send_email(to_email, "ChemLearn API 注册验证码", html)
