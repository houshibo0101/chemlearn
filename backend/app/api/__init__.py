from app.api.auth import router as auth_router
from app.api.questions import router as questions_router
from app.api.wrong_questions import router as wrong_questions_router
from app.api.ai import router as ai_router
from app.api.api_keys import router as api_keys_router
from app.api.open_platform import router as open_platform_router
from app.api.admin_users import router as admin_users_router
from app.api.classes import router as classes_router
from app.api.assignments import router as assignments_router
from app.api.exams import router as exams_router
from app.api.teacher import router as teacher_router
from app.api.offline import router as offline_router
from app.api.stats import router as stats_router
from app.api.admin_dashboard import router as admin_dashboard_router
from app.api.question_import import router as question_import_router
from app.api.open_platform_v2 import router as open_platform_v2_router
from app.api.knowledge_graph import router as knowledge_graph_router
from app.api.question_ext import router as question_ext_router
from app.api.practice_records import router as practice_records_router
from app.api.notifications import router as notifications_router
from app.api.papers import router as papers_router
from app.api.favorites import router as favorites_router
from app.api.ai_tasks import router as ai_tasks_router

__all__ = [
    "auth_router", "questions_router", "wrong_questions_router",
    "ai_router", "api_keys_router", "open_platform_router",
    "admin_users_router", "classes_router", "assignments_router",
    "exams_router", "teacher_router", "offline_router", "stats_router",
    "admin_dashboard_router", "question_import_router", "open_platform_v2_router",
    "knowledge_graph_router",
    "question_ext_router", "practice_records_router", "notifications_router",
    "papers_router", "favorites_router", "ai_tasks_router",
]
