"""角色权限常量（RBAC）与数据范围映射，见 D-03 §5/§13。"""

from typing import Dict, FrozenSet, Tuple

# 数据范围类型
SCOPE_NONE = "NONE"
SCOPE_SELF = "SELF"
SCOPE_CHILD = "CHILD"
SCOPE_CLASS = "CLASS"
SCOPE_SCHOOL = "SCHOOL"
SCOPE_ALL = "ALL"

ALL_PERMISSIONS = "*"

PERMISSIONS: Tuple[str, ...] = (
    "learn:content:read",
    "learn:kp:study",
    "learn:practice:start",
    "learn:practice:submit",
    "learn:stats:self:read",
    "learn:stats:child:read",
    "learn:stats:class:read",
    "learn:wrong:self",
    "learn:wrong:annotate",
    "learn:review:today",
    "learn:exam:take",
    "learn:exam:report:self",
    "learn:assignment:create",
    "learn:exam:grade",
    "content:textbook:write",
    "content:kp:write",
    "content:question:write",
    "content:exam:write",
    "content:review:decide",
    "content:publish",
    "family:binding:request",
    "family:binding:manage",
    "family:control:write",
    "family:report:read",
    "org:class:manage",
    "org:student:manage",
    "org:teacher:assign",
    "admin:user:manage",
    "admin:role:assign",
    "audit:log:read",
    "support:ticket:manage",
    "system:config:write",
    "user:profile:update",
    "user:grade:change",
    "data:export",
)

# 权限点 → 允许的数据范围（§13 附录）
PERMISSION_SCOPE: Dict[str, Tuple[str, ...]] = {
    "learn:content:read": (SCOPE_NONE,),
    "learn:kp:study": (SCOPE_SELF, SCOPE_CLASS),
    "learn:practice:start": (SCOPE_SELF,),
    "learn:practice:submit": (SCOPE_SELF,),
    "learn:stats:self:read": (SCOPE_SELF,),
    "learn:stats:child:read": (SCOPE_CHILD,),
    "learn:stats:class:read": (SCOPE_CLASS,),
    "learn:wrong:self": (SCOPE_SELF,),
    "learn:wrong:annotate": (SCOPE_SELF,),
    "learn:review:today": (SCOPE_SELF,),
    "learn:exam:take": (SCOPE_SELF,),
    "learn:exam:report:self": (SCOPE_SELF,),
    "learn:assignment:create": (SCOPE_CLASS,),
    "learn:exam:grade": (SCOPE_CLASS,),
    "content:textbook:write": (SCOPE_ALL,),
    "content:kp:write": (SCOPE_ALL,),
    "content:question:write": (SCOPE_ALL,),
    "content:exam:write": (SCOPE_ALL,),
    "content:review:decide": (SCOPE_ALL,),
    "content:publish": (SCOPE_ALL,),
    "family:binding:request": (SCOPE_SELF,),
    "family:binding:manage": (SCOPE_SELF, SCOPE_CHILD),
    "family:control:write": (SCOPE_CHILD,),
    "family:report:read": (SCOPE_CHILD,),
    "org:class:manage": (SCOPE_SCHOOL,),
    "org:student:manage": (SCOPE_SCHOOL, SCOPE_CLASS),
    "org:teacher:assign": (SCOPE_SCHOOL,),
    "admin:user:manage": (SCOPE_SCHOOL, SCOPE_ALL),
    "admin:role:assign": (SCOPE_SCHOOL, SCOPE_ALL),
    "audit:log:read": (SCOPE_SCHOOL, SCOPE_ALL),
    "support:ticket:manage": (SCOPE_SELF, SCOPE_ALL),
    "system:config:write": (SCOPE_ALL,),
    "user:profile:update": (SCOPE_SELF,),
    "user:grade:change": (SCOPE_SELF, SCOPE_SCHOOL),
    "data:export": (SCOPE_SCHOOL, SCOPE_ALL),
}

_STUDENT_PERMISSIONS: FrozenSet[str] = frozenset(
    {
        "learn:content:read",
        "learn:kp:study",
        "learn:practice:start",
        "learn:practice:submit",
        "learn:stats:self:read",
        "learn:wrong:self",
        "learn:wrong:annotate",
        "learn:review:today",
        "learn:exam:take",
        "learn:exam:report:self",
        "family:binding:manage",
        "support:ticket:manage",
        "user:profile:update",
        "user:grade:change",
    }
)

_PARENT_PERMISSIONS: FrozenSet[str] = frozenset(
    {
        "learn:content:read",
        "learn:stats:self:read",
        "learn:stats:child:read",
        "learn:exam:report:self",
        "family:binding:request",
        "family:binding:manage",
        "family:control:write",
        "family:report:read",
        "support:ticket:manage",
        "user:profile:update",
    }
)

_TEACHER_PERMISSIONS: FrozenSet[str] = frozenset(
    {
        "learn:content:read",
        "learn:kp:study",
        "learn:stats:self:read",
        "learn:stats:class:read",
        "learn:exam:report:self",
        "learn:assignment:create",
        "learn:exam:grade",
        "org:student:manage",
        "support:ticket:manage",
        "user:profile:update",
    }
)

_CONTENT_OPERATOR_PERMISSIONS: FrozenSet[str] = frozenset(
    {
        "learn:content:read",
        "learn:kp:study",
        "learn:stats:self:read",
        "content:textbook:write",
        "content:kp:write",
        "content:question:write",
        "content:exam:write",
        "content:publish",
        "user:profile:update",
    }
)

_AUDITOR_PERMISSIONS: FrozenSet[str] = frozenset(
    {
        "learn:content:read",
        "learn:stats:self:read",
        "learn:exam:report:self",
        "content:review:decide",
        "audit:log:read",
        "admin:user:manage",
        "user:profile:update",
    }
)

_CUSTOMER_SERVICE_PERMISSIONS: FrozenSet[str] = frozenset(
    {
        "learn:content:read",
        "learn:stats:self:read",
        "org:student:manage",
        "admin:user:manage",
        "support:ticket:manage",
        "user:profile:update",
    }
)

_SCHOOL_ADMIN_PERMISSIONS: FrozenSet[str] = _STUDENT_PERMISSIONS | frozenset(
    {
        "learn:stats:class:read",
        "learn:assignment:create",
        "learn:exam:grade",
        "org:class:manage",
        "org:student:manage",
        "org:teacher:assign",
        "admin:user:manage",
        "admin:role:assign",
        "audit:log:read",
        "data:export",
    }
)

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "guest": frozenset({"learn:content:read"}),
    "student": _STUDENT_PERMISSIONS,
    "parent": _PARENT_PERMISSIONS,
    "teacher": _TEACHER_PERMISSIONS,
    "head_teacher": _TEACHER_PERMISSIONS | frozenset({"org:class:manage"}),
    "school_admin": _SCHOOL_ADMIN_PERMISSIONS,
    "content_operator": _CONTENT_OPERATOR_PERMISSIONS,
    "auditor": _AUDITOR_PERMISSIONS,
    "customer_service": _CUSTOMER_SERVICE_PERMISSIONS,
    "super_admin": frozenset({ALL_PERMISSIONS}),
}

# 历史角色兼容：admin 视为 super_admin
ROLE_ALIASES = {"admin": "super_admin"}

# 角色默认数据范围
ROLE_SCOPE: Dict[str, str] = {
    "guest": SCOPE_NONE,
    "student": SCOPE_SELF,
    "parent": SCOPE_CHILD,
    "teacher": SCOPE_CLASS,
    "head_teacher": SCOPE_CLASS,
    "school_admin": SCOPE_SCHOOL,
    "content_operator": SCOPE_ALL,
    "auditor": SCOPE_ALL,
    "customer_service": SCOPE_ALL,
    "super_admin": SCOPE_ALL,
}


def normalize_role(role: str) -> str:
    return ROLE_ALIASES.get(role, role)


def permissions_for_role(role: str) -> FrozenSet[str]:
    return ROLE_PERMISSIONS.get(normalize_role(role), frozenset())


def scope_for_role(role: str) -> str:
    return ROLE_SCOPE.get(normalize_role(role), SCOPE_NONE)
