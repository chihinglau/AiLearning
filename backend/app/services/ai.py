"""P2-06 AI 讲解与错题归因服务：LLM 接入、规则兜底、额度控制。

默认 `llm_enabled=False` 时使用确定性规则讲解（基于题库解析与选项），
开启后调用 OpenAI 兼容的 `/chat/completions` 接口；外部调用失败自动回退规则，
保证教学场景始终可用。
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Protocol

from app.core import cache
from app.core.config import Settings, settings
from app.models.content import Question
from app.models.practice import WrongQuestion
from app.services import ai_prompt
from app.services import wrong_reason as wrong_reason_service

RULE_PROVIDER = "rule"
LLM_PROVIDER = "llm"
QUOTA_TTL_SECONDS = 3700

TYPE_LABELS = {
    "choice": "单选题",
    "multiple": "多选题",
    "fill": "填空题",
    "judge": "判断题",
    "calc": "计算题",
    "answer": "主观题",
    "listen": "听力题",
}

REASON_SUGGESTIONS = {
    "concept": ["回看知识点定义与典型例题，用自己的话复述一遍", "做 2 道同知识点基础题，确认概念边界"],
    "calculation": ["把计算过程分步写出来，逐步核对每一步", "限时练 3 道同类计算题，检查进位与符号"],
    "method": ["先写出解题框架再动笔，优先选择熟悉的方法", "对照参考答案复盘方法差异，整理成一页笔记"],
    "reading": ["圈出题干中的限制条件与问题对象再作答", "做完后回读题干，确认没有漏看关键条件"],
    "careless": ["作答后留 30 秒检查：单位、范围、抄写是否一致", "把易错点写在草稿区顶部作为提醒"],
    "other": ["整理本题的考点与正确步骤，形成错题卡片", "隔天复习一次，再做一道同类题巩固"],
}


class QuotaExceededError(Exception):
    """AI 讲解小时额度用尽。"""


def consume_quota(user_id: int, limit: int) -> int:
    """按用户+小时计数，返回剩余额度；超限抛 QuotaExceededError。"""
    bucket = datetime.utcnow().strftime("%Y%m%d%H")
    key = f"ai:quota:{user_id}:{bucket}"
    used = cache.get(key)
    used = int(used) if isinstance(used, (int, float)) else 0
    if used >= limit:
        raise QuotaExceededError()
    cache.set(key, used + 1, ttl=QUOTA_TTL_SECONDS)
    return max(0, limit - used - 1)


def _answer_text(answer: Optional[dict[str, Any]]) -> str:
    if not answer:
        return "（题库未提供答案）"
    value = answer.get("value")
    if value is None:
        return "（题库未提供答案）"
    if isinstance(value, (list, tuple)):
        return "、".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _question_type_label(q_type: str) -> str:
    return TYPE_LABELS.get(q_type, "题目")


def _cautions(q_type: str) -> list[str]:
    if q_type in ("choice", "multiple"):
        return ["注意区分“正确/不正确”“最多/至少”等设问方向", "多选题逐项判断，避免漏选或多选"]
    if q_type in ("fill", "calc"):
        return ["检查单位、取值范围与计算符号", "不要跳步，关键中间结果写在草稿上"]
    if q_type == "judge":
        return ["关注绝对化表述（一定、全部、必须）", "先找反例，再下结论"]
    return ["先列要点再展开，避免答非所问", "对照题目分值分配作答篇幅"]


@dataclass
class AIExplanation:
    question_id: int
    provider: str
    explanation: str
    steps: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)


@dataclass
class AIDiagnosis:
    wrong_id: int
    question_id: int
    provider: str
    reason: str
    reason_label: str
    confidence: str
    explanation: str
    suggestions: list[str] = field(default_factory=list)


class ChatProvider(Protocol):
    name: str

    def complete(self, messages: list[dict[str, str]]) -> str: ...


class OpenAICompatProvider:
    """OpenAI 兼容 Chat Completions 客户端（仅标准库，避免新增依赖）。"""

    name = LLM_PROVIDER

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: float) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 600,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")


def _build_provider(config: Settings) -> Optional[ChatProvider]:
    if not config.llm_enabled or not config.llm_api_key:
        return None
    return OpenAICompatProvider(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
        model=config.llm_model,
        timeout=config.llm_timeout_seconds,
    )


def _rule_explain(
    question: Question,
    *,
    user_answer: Optional[dict[str, Any]],
    kp_name: Optional[str],
    focus: Optional[str],
    max_chars: int,
) -> AIExplanation:
    stem = ai_prompt.sanitize_text((question.content or {}).get("stem", ""), 120)
    answer = ai_prompt.sanitize_text(_answer_text(question.answer), 60)
    analysis = ai_prompt.sanitize_text(question.analysis or "", 200)
    type_label = _question_type_label(question.q_type)

    head = analysis or (
        f"这是一道{type_label}，参考答案是「{answer}」。"
        "先判断题目考查的知识点，再按对应规则逐步推导。"
    )
    if kp_name:
        head = f"{head} 关联知识点「{ai_prompt.sanitize_text(kp_name, 60)}」，建议先回看定义与例题。"

    steps = [
        f"读题：明确问题是「{stem or '本题考点'}」，圈出限制条件。",
        "定位：判断题型与知识点，回忆对应定义、公式或判定规则。",
        f"作答：按规则推导，得到参考答案「{answer}」。",
        "检查：把结果代回题干，确认单位、范围与选项一致。",
    ]
    if focus == "concept":
        steps.insert(1, "概念：先用一句话说清本题涉及的定义，再套用到题干。")
    elif focus == "method":
        steps.insert(1, "方法：比较两种可行思路，选择步骤更少、更不易错的一种。")
    elif focus == "steps":
        steps.insert(2, "分步：每一步只做一件事，把中间结果写下来。")
    if user_answer and user_answer.get("value") is not None:
        steps.append(
            "对照：你的作答为「"
            + ai_prompt.sanitize_text(user_answer.get("value"), 60)
            + "」，重点找出与参考答案的差异。"
        )
    return AIExplanation(
        question_id=question.id,
        provider=RULE_PROVIDER,
        explanation=ai_prompt.sanitize_output(head, max_chars),
        steps=steps,
        cautions=_cautions(question.q_type),
    )


class AIService:
    def __init__(self, config: Optional[Settings] = None, provider: Optional[ChatProvider] = None):
        self._config = config or settings
        self._provider = provider if provider is not None else _build_provider(self._config)

    @property
    def enabled(self) -> bool:
        return self._provider is not None

    def explain(
        self,
        question: Question,
        *,
        user_answer: Optional[dict[str, Any]] = None,
        kp_name: Optional[str] = None,
        focus: Optional[str] = None,
    ) -> AIExplanation:
        result = _rule_explain(
            question,
            user_answer=user_answer,
            kp_name=kp_name,
            focus=focus,
            max_chars=self._config.ai_max_output_chars,
        )
        if self._provider is None:
            return result
        try:
            text = self._provider.complete(
                ai_prompt.build_explain_messages(
                    question, user_answer=user_answer, kp_name=kp_name, focus=focus
                )
            )
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
            return result
        cleaned = ai_prompt.sanitize_output(text, self._config.ai_max_output_chars)
        if not cleaned:
            return result
        return AIExplanation(
            question_id=result.question_id,
            provider=LLM_PROVIDER,
            explanation=cleaned,
            steps=result.steps,
            cautions=result.cautions,
        )

    def diagnose(
        self,
        question: Question,
        wrong: WrongQuestion,
        *,
        user_answer: Optional[dict[str, Any]] = None,
        kp_name: Optional[str] = None,
    ) -> AIDiagnosis:
        reason = wrong.wrong_reason or wrong_reason_service.classify_exam_wrong(
            question, user_answer
        )
        reason_label = wrong_reason_service.REASON_LABELS.get(reason, "其他")
        if wrong.wrong_count >= 3 or wrong.lapses >= 2:
            confidence = "high"
        elif wrong.wrong_count >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        answer = ai_prompt.sanitize_text(_answer_text(question.answer), 60)
        explanation = (
            f"本题累计做错 {wrong.wrong_count} 次，判断更接近「{reason_label}」类问题。"
            f"参考答案是「{answer}」，建议先复述相关规则，再按步骤重做一遍。"
        )
        if question.analysis:
            explanation = (
                f"{ai_prompt.sanitize_text(question.analysis, 160)} "
                f"结合错误次数，暂归因为「{reason_label}」。"
            )
        provider = RULE_PROVIDER
        if self._provider is not None:
            try:
                text = self._provider.complete(
                    ai_prompt.build_diagnose_messages(
                        question,
                        user_answer=user_answer,
                        reason_label=reason_label,
                        wrong_count=wrong.wrong_count,
                        lapses=wrong.lapses,
                        kp_name=kp_name,
                    )
                )
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
                text = ""
            cleaned = ai_prompt.sanitize_output(text, self._config.ai_max_output_chars)
            if cleaned:
                explanation = cleaned
                provider = LLM_PROVIDER

        return AIDiagnosis(
            wrong_id=wrong.id,
            question_id=question.id,
            provider=provider,
            reason=reason,
            reason_label=reason_label,
            confidence=confidence,
            explanation=explanation,
            suggestions=list(REASON_SUGGESTIONS.get(reason, REASON_SUGGESTIONS["other"])),
        )
