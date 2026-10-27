"""
一次性工具 v2：把 15 份高考真题导入脚本的内嵌题目数据安全提取为 JSON。

两类脚本：
1. batch* 系列：模块级构建 QUESTIONS 列表，main() 有 __main__ 守卫 → 直接 exec 收集。
2. 省卷/gaokao 系列：数据在 async 函数内部，通过 Question(...) + db.add(...) 入库，
   且部分脚本 import 即执行 → 注入假模块（app.* / sqlalchemy）后 exec，
   用假 Question/db 捕获数据，绝不触碰真实数据库。
"""
import asyncio
import io
import json
import os
import sys
import types
from contextlib import redirect_stdout
from types import SimpleNamespace

BACKEND = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BACKEND, "import_data")
os.makedirs(OUT_DIR, exist_ok=True)

MODULE_LEVEL_SCRIPTS = [
    "import_gaokao_all.py",
    "import_gaokao_batch2.py",
    "import_gaokao_batch3.py",
    "import_gaokao_batch4.py",
    "import_gaokao_batch5.py",
    "import_gaokao_batch6.py",
    "import_gaokao_batch7.py",
    "import_gaokao_batch8.py",
    "import_gaokao_batch9.py",
    "import_gaokao_batch10.py",
    "import_gaokao_batch11.py",
]
ASYNC_SCRIPTS = [
    "import_gaokao.py",
    "import_2024_guangdong.py",
    "import_2024_heijiliao.py",
    "import_2024_shandong.py",
]

captured = []


class FakeQuestion:
    """捕获构造参数的假 Question 模型"""

    # 类级占位属性：脚本里 select(Question).where(Question.xxx == v) 需要可比较
    question_code = ""
    title = ""
    id = 0

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        captured.append(dict(kwargs))


class FakeResult:
    def scalar_one(self):
        return SimpleNamespace(id=1, username="admin")

    def scalar_one_or_none(self):
        return None


class FakeSelect:
    def where(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self


class FakeDB:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def execute(self, *a, **k):
        return FakeResult()

    def add(self, obj):
        pass  # 数据已在 FakeQuestion.__init__ 捕获

    def add_all(self, objs):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def refresh(self, *a):
        pass

    async def flush(self):
        pass


class _Placeholder:
    """可调用 + 可取属性的占位：QuestionType('SINGLE') / .value 等用法都兼容"""

    def __init__(self, name=""):
        self._name = name

    def __call__(self, *args, **kwargs):
        return args[0] if args else None

    def __getattr__(self, item):
        return _Placeholder(f"{self._name}.{item}")

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name


class PermissiveModule(types.ModuleType):
    """任何缺失属性都返回占位对象，兼容脚本里各种 from-import"""

    def __getattr__(self, name):
        placeholder = _Placeholder(name)
        setattr(self, name, placeholder)
        return placeholder


def inject_fakes():
    """把 app.* 与 sqlalchemy 替换为假模块，防止脚本触库"""
    def mod(name, **attrs):
        m = PermissiveModule(name)
        m.__dict__.update(attrs)
        m.__path__ = []
        sys.modules[name] = m
        return m

    app_pkg = mod("app")
    mod("app.core")
    mod("app.core.database", AsyncSessionLocal=FakeDB, engine=None, init_db=lambda: None)
    mod("app.models")
    mod("app.models.question", Question=FakeQuestion)
    mod("app.models.user", User=_Placeholder("User"))
    mod("sqlalchemy", select=lambda *a, **k: FakeSelect(), func=SimpleNamespace(count=lambda *a: 0))
    return app_pkg


def remove_fakes():
    for name in ["app", "app.core", "app.core.database", "app.models",
                 "app.models.question", "app.models.user", "sqlalchemy"]:
        sys.modules.pop(name, None)


report = []
total = 0

# ---- 第一类：模块级 QUESTIONS ----
for name in MODULE_LEVEL_SCRIPTS:
    path = os.path.join(BACKEND, name)
    src = open(path, encoding="utf-8").read()
    ns = {"__name__": "_extract_", "__file__": path}
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compile(src, path, "exec"), ns)
    qs = ns.get("QUESTIONS", [])
    out = os.path.join(OUT_DIR, name.replace(".py", ".json"))
    json.dump(qs, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    report.append((name, len(qs)))
    total += len(qs)
    print(f"OK  {name}: {len(qs)} 题")

# ---- 第二类：async 函数内数据 ----
for name in ASYNC_SCRIPTS:
    path = os.path.join(BACKEND, name)
    src = open(path, encoding="utf-8").read()
    captured.clear()
    inject_fakes()
    try:
        ns = {"__name__": "_extract_", "__file__": path}
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(compile(src, path, "exec"), ns)
        # 若脚本有 __main__ 守卫（import_gaokao.py），手动调用
        fn = ns.get("import_questions")
        if fn and not captured:
            asyncio.run(fn())
    finally:
        remove_fakes()
    qs = captured
    out = os.path.join(OUT_DIR, name.replace(".py", ".json"))
    json.dump(qs, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    report.append((name, len(qs)))
    total += len(qs)
    print(f"OK  {name}: {len(qs)} 题")

print(f"\n合计提取 {total} 道题 -> {OUT_DIR}")
for n, c in report:
    assert c > 0, f"{n} 提取为 0，需人工检查"
print("全部脚本提取成功")
