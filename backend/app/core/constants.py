"""学科 / 学段 / 角色等教育业务枚举常量。"""

SUBJECTS = (
    "chinese",
    "math",
    "english",
    "physics",
    "chemistry",
    "biology",
    "history",
    "geography",
    "politics",
)

STAGES = ("primary", "junior", "senior")

ROLES = ("student", "parent", "admin")

QUESTION_TYPES = ("choice", "multiple", "fill", "judge", "calc", "listen")

WRONG_REASONS = ("concept", "calc", "careless", "unknown", "other")
