"""
站内通知与错题重练接口测试
- 通知：列表/未读数/已读/发布作业自动通知班级学生
- 错题重练：repractice 返回错题原题
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password, create_access_token
from app.models import User, UserRole, ClassRoom, TeacherClass, Assignment, AssignmentClass, AssignmentStatus, Notification, Question, WrongQuestion
from sqlalchemy import select


async def _ensure_users(db):
    """创建老师 + 2个学生 + 班级 + 草稿作业（幂等）"""
    teacher = (await db.execute(select(User).where(User.username == "t_notify"))).scalar_one_or_none()
    if teacher:
        return teacher
    teacher = User(username="t_notify", email="t_notify@test.com", hashed_password=hash_password("Passw0rd123"),
                   full_name="通知老师", role=UserRole.TEACHER, is_active=True)
    db.add(teacher)
    cls = ClassRoom(name="通知测试班", grade="高一", join_code="NTFY001")
    db.add(cls)
    await db.flush()
    db.add(TeacherClass(teacher_id=teacher.id, class_id=cls.id))
    for i in (1, 2):
        db.add(User(username=f"s_notify{i}", email=f"s_notify{i}@test.com",
                    hashed_password=hash_password("Passw0rd123"), full_name=f"学生{i}",
                    role=UserRole.STUDENT, is_active=True, class_id=cls.id))
    a = Assignment(teacher_id=teacher.id, title="通知测试作业", description="用于验证发布通知",
                   status=AssignmentStatus.DRAFT)
    db.add(a)
    await db.flush()
    db.add(AssignmentClass(assignment_id=a.id, class_id=cls.id))
    await db.commit()
    return teacher


@pytest.mark.asyncio
async def test_publish_assignment_notifies_students(client, db_session):
    teacher = await _ensure_users(db_session)
    token = create_access_token(str(teacher.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 找到草稿作业
    a = (await db_session.execute(select(Assignment).where(Assignment.title == "通知测试作业"))).scalars().first()
    assert a, "测试作业不存在"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/assignments/{a.id}/publish", headers=headers)
        assert resp.status_code == 200, resp.text

        # 学生收到通知
        stu = (await db_session.execute(select(User).where(User.username == "s_notify1"))).scalar_one()
        stu_token = create_access_token(str(stu.id))
        resp2 = await ac.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {stu_token}"})
        assert resp2.status_code == 200
        assert resp2.json()["count"] >= 1, "发布作业后学生未收到通知"

        # 通知列表里有作业类型
        resp3 = await ac.get("/api/v1/notifications", headers={"Authorization": f"Bearer {stu_token}"})
        items = resp3.json()["items"]
        assert any(n["ntype"] == "assignment" and n["title"].startswith("新作业") for n in items)

        # 全部已读
        resp4 = await ac.post("/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {stu_token}"})
        assert resp4.status_code == 200
        resp5 = await ac.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {stu_token}"})
        assert resp5.json()["count"] == 0


@pytest.mark.asyncio
async def test_repractice_returns_questions(client, db_session):
    """错题重练：学生的错题应能取回完整题目（不含答案）"""
    # 准备：一道题 + 学生错题记录
    q = Question(question_code="QTST0001", title="重练测试题", content="下列属于氧化物的是",
                 question_type="single", difficulty="easy", grade="高一",
                 options='[{"key":"A","text":"水"},{"key":"B","text":"氧气"}]', answer="A")
    db_session.add(q)
    await db_session.flush()
    stu = (await db_session.execute(select(User).where(User.username == "s_notify2"))).scalar_one()
    db_session.add(WrongQuestion(user_id=stu.id, question_id=q.id, wrong_count=1, user_answer="B"))
    await db_session.commit()

    token = create_access_token(str(stu.id))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/wrong-questions/repractice", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = next(i for i in data["items"] if i["question_code"] == "QTST0001")
        assert "answer" not in item, "重练接口不应返回答案"
        assert item["options"] is not None
