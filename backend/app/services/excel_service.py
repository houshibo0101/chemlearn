"""
Excel 导出服务
"""
import io
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from app.models import WrongQuestion, User


HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
CELL_FONT = Font(name="微软雅黑", size=10)
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


class ExcelExportService:
    @staticmethod
    async def export_wrong_questions(
        db: AsyncSession,
        user_id: int | None = None,
    ) -> bytes:
        """
        导出错题 Excel
        列：姓名、学段、错题题目、错的次数、最后一次错的时间
        重复错题已在数据库层去重（同一用户同一题目唯一）
        """
        query = select(WrongQuestion).options(
            joinedload(WrongQuestion.user),
            joinedload(WrongQuestion.question),
        )
        if user_id:
            query = query.where(WrongQuestion.user_id == user_id)
        query = query.order_by(WrongQuestion.last_wrong_at.desc())

        result = await db.execute(query)
        wrong_list = result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = "错题记录"

        # 表头
        headers = ["序号", "题目编号", "姓名", "学段", "错题题目", "错的次数", "最后一次错的时间"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = CENTER
            cell.border = THIN_BORDER

        # 数据
        for idx, wq in enumerate(wrong_list, 1):
            row = idx + 1
            user = wq.user
            question = wq.question
            q_code = question.question_code if question and question.question_code else (f"Q{question.id:04d}" if question else "")
            values = [
                idx,
                q_code,
                user.full_name if user and user.full_name else (user.username if user else ""),
                user.grade if user else "",
                question.title if question else "",
                wq.wrong_count,
                wq.last_wrong_at.strftime("%Y-%m-%d %H:%M:%S") if wq.last_wrong_at else "",
            ]
            for col, v in enumerate(values, 1):
                cell = ws.cell(row=row, column=col, value=v)
                cell.font = CELL_FONT
                cell.border = THIN_BORDER
                cell.alignment = LEFT if col == 5 else CENTER

        # 列宽
        widths = [6, 12, 12, 10, 60, 10, 20]
        for col, w in enumerate(widths, 1):
            ws.column_dimensions[chr(64 + col)].width = w

        # 冻结首行
        ws.freeze_panes = "A2"

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
