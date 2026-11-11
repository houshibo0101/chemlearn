# -*- coding: utf-8 -*-
"""连连看题目的批量导入解析

支持三种格式：
  · .xlsx  第一张工作表，A 列左项、B 列右项、C 列提示（可选）
  · .csv   同上，逗号分隔（也兼容制表符）
  · .txt   每行「左项 | 右项 | 提示」，竖线/制表符均可
返回 (pairs, warnings)，pairs 为 [{"left_text", "right_text", "hint"}]。
"""
import csv
import io
import re

MAX_PAIRS = 30
HEADER_WORDS = {
    "左项", "左", "左侧", "名称", "物质", "物质名称", "题", "题目", "术语",
    "右项", "右", "右侧", "俗称", "说明", "答案", "匹配",
}
_WS = re.compile(r"\s+")


def _norm_header(cell: str) -> str:
    return _WS.sub("", (cell or "").strip().lower())


def _is_header(row: list[str]) -> bool:
    if not row:
        return False
    first = _norm_header(row[0])
    second = _norm_header(row[1]) if len(row) > 1 else ""
    return first in HEADER_WORDS and (not second or second in HEADER_WORDS)


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip()


def _rows_from_xlsx(data: bytes):
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ValueError("服务器缺少 openpyxl，暂时无法解析 Excel")
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheet = workbook.active
    rows = []
    for row in sheet.iter_rows(values_only=True):
        rows.append([_clean(cell) for cell in row])
    workbook.close()
    return rows


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _rows_from_csv(data: bytes):
    text = _decode_text(data)
    sample = text[:4096]
    delimiter = ","
    if sample.count("\t") > sample.count(","):
        delimiter = "\t"
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return [[_clean(cell) for cell in row] for row in reader]


def _rows_from_txt(data: bytes):
    text = _decode_text(data)
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "｜" in line:
            parts = line.split("｜")
        elif "|" in line:
            parts = line.split("|")
        elif "\t" in line:
            parts = line.split("\t")
        else:
            parts = [line]
        rows.append([_clean(part) for part in parts])
    return rows


def parse_file(filename: str, data: bytes):
    """解析上传文件，返回 (pairs, warnings)"""
    if not filename:
        raise ValueError("请选择要上传的文件")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("文件太大（上限 5 MB）")

    if ext == "xlsx":
        rows = _rows_from_xlsx(data)
    elif ext == "csv":
        rows = _rows_from_csv(data)
    elif ext in ("txt", "text"):
        rows = _rows_from_txt(data)
    else:
        raise ValueError("仅支持 .xlsx / .csv / .txt 文件")

    warnings = []
    pairs = []
    seen = set()
    for index, row in enumerate(rows, 1):
        if not any(row):
            continue
        if _is_header(row):
            continue
        left = _clean(row[0]) if len(row) > 0 else ""
        right = _clean(row[1]) if len(row) > 1 else ""
        hint = _clean(row[2]) if len(row) > 2 else ""
        if not left and not right:
            continue
        if not left or not right:
            warnings.append("第 %d 行只有一列，已跳过" % index)
            continue
        if left == right:
            warnings.append("第 %d 行左右内容相同，已跳过" % index)
            continue
        key = (left, right)
        if key in seen:
            warnings.append("第 %d 行与前面的内容重复，已跳过" % index)
            continue
        seen.add(key)
        if len(left) > 200 or len(right) > 200:
            warnings.append("第 %d 行内容超过 200 字，已跳过" % index)
            continue
        pairs.append({"left_text": left, "right_text": right, "hint": hint or None})
        if len(pairs) >= MAX_PAIRS:
            warnings.append("最多支持 %d 对，后面的内容已忽略" % MAX_PAIRS)
            break

    if len(pairs) < 2:
        raise ValueError("至少需要 2 对有效内容（当前 %d 对）。%s"
                         % (len(pairs), "；".join(warnings[:3])))
    return pairs, warnings
