# AI 配置

系统用 OpenAI 兼容协议接大模型，默认对接**火山引擎方舟**。

---

## 配置项

编辑 `backend/.env`：

```ini
AI_API_KEY=ark-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxxx
AI_API_BASE=https://ark.cn-beijing.volces.com/api/v3
AI_MODEL=doubao-seed-2-0-mini-260428
AI_EXPLAIN_MODEL=deepseek-v4-flash-ga-260731
AI_TIMEOUT=180
```

| 变量 | 必填 | 说明 |
|---|---|---|
| `AI_API_KEY` | 是 | 火山引擎方舟的 API Key |
| `AI_API_BASE` | 否 | 默认火山方舟地址，换成别家时改这里 |
| `AI_MODEL` | 否 | 主模型：问答、套卷生成、变式题 |
| `AI_EXPLAIN_MODEL` | 否 | 解析模型：错题讲解、主观题阅卷。留空则用 `AI_MODEL` |
| `AI_TIMEOUT` | 否 | 单次请求超时（秒），长文本解析建议 180 |

改完重启服务：

```bash
sudo systemctl restart study-chem
```

> **部署器已经包含这一步**：在部署界面填 Key 和模型，会自动写入并生效。

---

## 双模型怎么分工

```
AI_MODEL           →  AI 问答、套卷结构化、变式题生成
AI_EXPLAIN_MODEL   →  错题讲解、主观题阅卷
```

分开的原因：套卷生成要长文本转结构化 JSON，看重提取能力；讲解和阅卷看重理解与表达，两者擅长的不一样。

实测组合：

- 生成：`doubao-seed-2-0-mini-260428`（快、便宜）
- 解析：`deepseek-v4-flash-ga-260731`（中文讲解质量更好）

只想配一个模型也行，`AI_EXPLAIN_MODEL` 留空即可。

---

## 换成别家模型

只要兼容 OpenAI 的 `/chat/completions` 协议就能接：

```ini
# OpenAI
AI_API_BASE=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini

# DeepSeek
AI_API_BASE=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat

# 通义千问（DashScope 兼容模式）
AI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen-plus
```

> **套卷功能需要多模态能力**（扫描件识别要发图片）。
> 纯文本模型也能跑，但上传扫描版 PDF 会失败，只能传文字型 PDF 或 TXT。

---

## 报错对照

| 报错 | 原因 | 处理 |
|---|---|---|
| `AI 服务未配置（缺少 AI_API_KEY）` | `.env` 没配或没被读到 | 检查文件路径 `backend/.env`，重启服务 |
| `HTTP 401` | Key 无效 | 去控制台确认 Key 是否启用 |
| `HTTP 403 AccountOverdueError` | **账号欠费** | 充值，这个没法绕 |
| `HTTP 404` | 模型名写错，或该模型未开通 | 控制台确认模型 ID（不是显示名） |
| `HTTP 429` | 触发限流 | 降并发或等一会儿；本项目 OCR 默认并发 3 |
| `请求超时` | 长文本解析慢 | 把 `AI_TIMEOUT` 调到 240 |

---

## 用量与成本

系统会记录每次调用的 token 消耗，管理员在「数据看板」能看：

```
ai_usage 表：user_id / model / prompt_tokens / completion_tokens / usage_type
```

参考量级（实测）：

| 操作 | 调用次数 | 说明 |
|---|---|---|
| 生成一份 8 页扫描卷 | 8（OCR）+ 3（结构化） | 约 4 分钟 |
| 生成一份文字型 PDF 卷 | 3（结构化） | 约 2 分钟 |
| 错题 AI 讲解 | 1 | 10–30 秒 |
| 变式题 3 道 | 1 | 20–40 秒 |
| 套卷交卷判分 | 1（批量判所有主观题） | 5–15 秒 |

---

## 安全提示

- `.env` 已在 `.gitignore` 里，不会进仓库
- 部署器写 `.env` 时会 `chmod 600`
- 数据库里不存 Key，只在内存里用
- 如果 Key 泄露，去控制台吊销重新生成，改 `.env` 重启即可
