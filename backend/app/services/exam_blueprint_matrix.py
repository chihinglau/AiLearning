"""试卷蓝图矩阵（PG-02）：g1–g9 × 语文/数学/英语 × 单元/期中/期末 = 81 条。

PM 2026-11-16 裁决：
- 不接受「降级卷」：语文必须有习作（q_type=composition）、英语必须有听力（q_type=listening），
  题库没有这两种题型时由 exam_paper.generate_paper 直接拒绝出卷；
- 期末/期中区分上/下册：由调用方传 semester 对应的 textbook_id + scope 决定范围（蓝图不绑册）；
- 作废 EXAM_TYPE_WEIGHT（题量系数），以蓝图固定题量为唯一口径；
- 单元卷 60 分 / 期中期末 100 分。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exam import ExamBlueprint

LABEL = {"chinese": "语文", "math": "数学", "english": "英语"}
SUFFIX = {"unit": "单元测试卷", "midterm": "期中模拟卷", "final": "期末模拟卷"}

# 每个卷型的分节模板；composition / listening 为题库尚未建设的题型（严格校验用）
_SECTIONS: dict[str, dict[str, list[dict]]] = {
    "math": {
        "unit": [
            {"name": "一、选择题", "q_type": "choice", "count": 4, "score_each": 4, "band": "easy"},
            {"name": "二、填空题", "q_type": "fill", "count": 5, "score_each": 4, "band": "medium"},
            {"name": "三、计算与解答", "q_type": "answer", "count": 3, "score_each": 8, "band": "hard"},
        ],
        # v2.20：期末卷 cap 被题量卡死（universe 44–66，22 题只有 0.33–0.50）→ 25 题。
        # 期中只考半册（universe 19–22），22 题已接近打满，加量只会逼出重复题，故保持 22。
        "midterm": [
            {"name": "一、选择题", "q_type": "choice", "count": 10, "score_each": 3, "band": "easy"},
            {"name": "二、填空题", "q_type": "fill", "count": 6, "score_each": 3, "band": "medium"},
            {"name": "三、计算与证明", "q_type": "answer", "count": 4, "score_each": 8, "band": "medium"},
            {"name": "四、综合应用", "q_type": "answer", "count": 2, "score_each": 10, "band": "hard"},
        ],
        "final": [
            {"name": "一、选择题", "q_type": "choice", "count": 12, "score_each": 3, "band": "easy"},
            {"name": "二、填空题", "q_type": "fill", "count": 8, "score_each": 3, "band": "medium"},
            {"name": "三、计算与证明", "q_type": "answer", "count": 4, "score_each": 8, "band": "medium"},
            {"name": "四、综合应用", "q_type": "answer", "count": 1, "score_each": 8, "band": "hard"},
        ],
    },
    "chinese": {
        "unit": [
            {"name": "一、积累与运用", "q_type": "fill", "count": 8, "score_each": 2, "band": "easy"},
            {"name": "二、选择题", "q_type": "choice", "count": 4, "score_each": 3, "band": "easy"},
            {"name": "三、阅读理解", "q_type": "answer", "count": 2, "score_each": 10, "band": "medium"},
            {"name": "四、习作", "q_type": "composition", "count": 1, "score_each": 12, "band": "hard"},
        ],
        # v2.20：期中 18 → 24 题（半册 universe 23–26，24 题基本能打满且不逼重复）；
        # 期末 18 → 28 题（全册 universe 39–47，cap 从 0.38 抬到 ~0.60）。习作固定 30 分。
        "midterm": [
            {"name": "一、积累与运用", "q_type": "fill", "count": 10, "score_each": 2, "band": "easy"},
            {"name": "二、选择题", "q_type": "choice", "count": 10, "score_each": 2, "band": "easy"},
            {"name": "三、阅读理解", "q_type": "answer", "count": 3, "score_each": 10, "band": "medium"},
            {"name": "四、习作", "q_type": "composition", "count": 1, "score_each": 30, "band": "hard"},
        ],
        "final": [
            {"name": "一、积累与运用", "q_type": "fill", "count": 11, "score_each": 2, "band": "easy"},
            {"name": "二、选择题", "q_type": "choice", "count": 12, "score_each": 2, "band": "easy"},
            {"name": "三、阅读理解", "q_type": "answer", "count": 4, "score_each": 6, "band": "medium"},
            {"name": "四、习作", "q_type": "composition", "count": 1, "score_each": 30, "band": "hard"},
        ],
    },
    "english": {
        "unit": [
            {"name": "一、听力", "q_type": "listening", "count": 8, "score_each": 1, "band": "easy"},
            {"name": "二、单项选择", "q_type": "choice", "count": 8, "score_each": 2, "band": "easy"},
            {"name": "三、词汇填空", "q_type": "fill", "count": 8, "score_each": 2, "band": "medium"},
            {"name": "四、阅读理解", "q_type": "choice", "count": 4, "score_each": 5, "band": "hard"},
        ],
        "midterm": [
            {"name": "一、听力", "q_type": "listening", "count": 10, "score_each": 2, "band": "easy"},
            {"name": "二、单项选择", "q_type": "choice", "count": 12, "score_each": 2, "band": "easy"},
            {"name": "三、词汇与句型填空", "q_type": "fill", "count": 10, "score_each": 2, "band": "medium"},
            {"name": "四、阅读理解", "q_type": "choice", "count": 6, "score_each": 3, "band": "medium"},
            {"name": "五、书面表达", "q_type": "composition", "count": 1, "score_each": 18, "band": "hard"},
        ],
        "final": [
            {"name": "一、听力", "q_type": "listening", "count": 10, "score_each": 2, "band": "easy"},
            {"name": "二、单项选择", "q_type": "choice", "count": 12, "score_each": 2, "band": "easy"},
            {"name": "三、词汇与句型填空", "q_type": "fill", "count": 10, "score_each": 2, "band": "medium"},
            {"name": "四、阅读理解", "q_type": "choice", "count": 6, "score_each": 3, "band": "medium"},
            {"name": "五、书面表达", "q_type": "composition", "count": 1, "score_each": 18, "band": "hard"},
        ],
    },
}

MIX = {"easy": 0.6, "medium": 0.3, "hard": 0.1}

# 听力节暂以选择题替代（走查 D-1，2026-11-18）：
# 题库 listening 题型已建设，但 Question 没有音频字段、作答页也没有播放控件，
# 学生打开「听录音，选出……」只能盲选，属于 P0 不可作答缺陷。
# 音频资产（Question.audio_url + 播放控件 + 逐题音频）接入后，把该开关置 False
# 即恢复原 listening 分节；题量/分值不变，因此不影响总分与蓝图口径。
LISTENING_AS_CHOICE = True


def _apply_listening_fallback() -> None:
    """把英语分节里的 listening 换成等题量等分的 choice，名称同步改为非听力表述。"""
    if not LISTENING_AS_CHOICE:
        return
    for sections in _SECTIONS.get("english", {}).values():
        for section in sections:
            if section.get("q_type") == "listening":
                section["q_type"] = "choice"
                section["name"] = str(section["name"]).replace("听力", "基础选择")


_apply_listening_fallback()

LEGACY_CODES = [
    "math_primary_unit", "chinese_primary_unit", "english_primary_unit",
    "math_primary_midterm", "math_primary_final",
    "chinese_primary_midterm", "chinese_primary_final",
    "english_primary_midterm", "english_primary_final",
]


def _time_limit(grade: int, exam_type: str) -> int:
    primary = grade <= 6
    if exam_type == "unit":
        return 40
    if exam_type == "midterm":
        return 60 if primary else 90
    return 90 if primary else 120


def build_specs() -> list[dict]:
    specs: list[dict] = []
    for grade in range(1, 10):
        for subject in ("chinese", "math", "english"):
            for exam_type in ("unit", "midterm", "final"):
                sections = _SECTIONS[subject][exam_type]
                total = sum(s["count"] * s["score_each"] for s in sections)
                specs.append({
                    "code": f"g{grade}_{subject}_{exam_type}",
                    "name": f"{grade}年级{LABEL[subject]}{SUFFIX[exam_type]}（自主题库生成）",
                    "subject": subject,
                    "grade": grade,
                    "exam_type": exam_type,
                    "total_score": total,
                    "time_limit_min": _time_limit(grade, exam_type),
                    "sections": sections,
                    "kp_coverage_min": 0.9 if exam_type == "unit" else 0.8,
                    "difficulty_mix": MIX,
                    "is_active": True,
                })
    return specs


def apply_matrix(db: Session, *, deactivate_legacy: bool = True) -> dict[str, int]:
    specs = build_specs()
    created = updated = 0
    for spec in specs:
        row = db.scalar(select(ExamBlueprint).where(ExamBlueprint.code == spec["code"]))
        if row is None:
            db.add(ExamBlueprint(**spec))
            created += 1
            continue
        for key, value in spec.items():
            if key == "code":
                continue
            setattr(row, key, value)
        updated += 1

    deactivated = 0
    if deactivate_legacy:
        for code in LEGACY_CODES:
            row = db.scalar(select(ExamBlueprint).where(ExamBlueprint.code == code))
            if row is not None and row.is_active:
                row.is_active = False
                deactivated += 1

    db.commit()
    return {"created": created, "updated": updated, "deactivated": deactivated, "total": len(specs)}
