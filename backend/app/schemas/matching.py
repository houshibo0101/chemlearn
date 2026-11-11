# -*- coding: utf-8 -*-
"""化学连连看：请求/响应校验"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CATEGORIES = ("substance", "functional_group", "equation", "common_name", "mixed")
CategoryType = Literal["substance", "functional_group", "equation", "common_name", "mixed"]
DifficultyType = Literal["easy", "medium", "hard"]

MAX_PAIRS = 30
MIN_PAIRS = 2


class MatchingPairIn(BaseModel):
    left_text: str = Field(min_length=1, max_length=200)
    right_text: str = Field(min_length=1, max_length=200)
    hint: str | None = Field(default=None, max_length=300)

    @field_validator("left_text", "right_text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("配对内容不能为空")
        return value

    @field_validator("hint")
    @classmethod
    def _strip_hint(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None


class MatchingSetIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    category: CategoryType = "mixed"
    difficulty: DifficultyType = "medium"
    grade: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    pairs: list[MatchingPairIn] = Field(min_length=MIN_PAIRS, max_length=MAX_PAIRS)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise ValueError("标题不能为空")
        return value

    @field_validator("description", "grade")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None

    @model_validator(mode="after")
    def _check_pairs(self):
        lefts = [p.left_text for p in self.pairs]
        rights = [p.right_text for p in self.pairs]

        for pair in self.pairs:
            if pair.left_text == pair.right_text:
                raise ValueError("左项和右项不能完全相同：%s" % pair.left_text)

        dup_left = {x for x in lefts if lefts.count(x) > 1}
        if dup_left:
            raise ValueError("左项有重复：%s" % "、".join(sorted(dup_left)[:5]))
        dup_right = {x for x in rights if rights.count(x) > 1}
        if dup_right:
            raise ValueError("右项有重复：%s" % "、".join(sorted(dup_right)[:5]))
        return self


class MatchingRecordIn(BaseModel):
    score: int = Field(ge=0, le=2000)
    mistakes: int = Field(ge=0, le=500)
    pairs_total: int = Field(ge=MIN_PAIRS, le=MAX_PAIRS)
    max_combo: int = Field(ge=0, le=MAX_PAIRS)
    duration_seconds: int = Field(ge=1, le=7200)
    pairs_matched: int | None = Field(default=None, ge=0, le=MAX_PAIRS)

    @model_validator(mode="after")
    def _check_score(self):
        # 每对最多 10 分基础分 + 连击奖励，客户端再怎么算也不该超过 30 分/对
        if self.score > self.pairs_total * 30:
            raise ValueError("得分异常，请重新开始")
        if self.mistakes > self.pairs_total * 20:
            raise ValueError("错误次数异常")
        return self
