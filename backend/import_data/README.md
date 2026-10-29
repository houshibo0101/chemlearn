# 题库数据（import_data）

这个目录用来放待导入的题库 JSON。**题库本身不随源码分发**，需要单独下载：

**下载地址：<https://github.com/houshibo0101/chemlearn/releases/tag/question-bank-v1>**

拿到 `chemlearn-question-bank-453.zip`（453 道高考化学题）后，解压把里面的 `*.json` 放到本目录，然后在 `backend/` 下执行：

```bash
python import_gaokao_unified.py
```

导入前请确保后端至少启动过一次（首次启动会自动建表），并且数据库里没有同名 `question_code` 的题目（重复导入会跳过或覆盖，取决于脚本参数）。

## JSON 格式

每个文件是一个数组，元素为一道题：

```json
[
  {
    "question_code": "GD2024-01",
    "title": "化学与生活",
    "content": "题干正文……",
    "question_type": "single_choice",
    "difficulty": "easy",
    "grade": "高三",
    "knowledge_point": "化学基本概念",
    "options": [{"key": "A", "value": "选项内容"}, {"key": "B", "value": "……"}],
    "answer": "A",
    "analysis": "解析文字……",
    "sub_questions": []
  }
]
```

| 字段 | 说明 |
|---|---|
| `question_code` | 题目唯一编号，重复会冲突，建议按来源自编 |
| `question_type` | `single_choice` / `multiple_choice` / `fill_blank` / `calculation` 等 |
| `difficulty` | `easy` / `medium` / `hard` |
| `options` | 选择题的选项数组，非选择题可为空 |
| `answer` | 正确答案，选择题为主题号（如 `A`），填空题为文本 |
| `analysis` | 解析，会显示在答题结果里 |

也可以不用 JSON：登录管理员后，在「题库管理」里手工新增，或用 Excel / PDF 批量导入。

## 说明

本目录的 `*.json` 已在 `.gitignore` 中忽略，避免自己导入的题库或商业题库被误提交到公开仓库。
