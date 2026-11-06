import pytest
from fastapi import HTTPException

from app.api.deps import (
    current_user_permissions,
    current_user_scope,
    has_permission,
    require_permission,
)
from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSIONS,
    PERMISSION_SCOPE,
    ROLE_PERMISSIONS,
    permissions_for_role,
    scope_for_role,
)
from app.core.scope import scope_for_permission
from app.models.user import User


def _user(role: str) -> User:
    return User(phone=f"phone-{role}", password_hash="hash", nickname=role, role=role)


def test_all_permissions_have_scope_mapping() -> None:
    assert set(PERMISSIONS) == set(PERMISSION_SCOPE)


def test_role_permissions_are_known() -> None:
    for role in ("student", "parent", "teacher", "head_teacher", "school_admin"):
        assert permissions_for_role(role) <= set(PERMISSIONS), role


def test_student_and_parent_permission_boundaries() -> None:
    student = _user("student")
    parent = _user("parent")

    assert has_permission(student, "learn:practice:submit")
    assert not has_permission(student, "learn:stats:child:read")

    assert has_permission(parent, "learn:stats:child:read")
    assert not has_permission(parent, "learn:practice:submit")


def test_legacy_admin_maps_to_super_admin() -> None:
    admin = _user("admin")
    assert has_permission(admin, "admin:role:assign")
    assert permissions_for_role("admin") == {ALL_PERMISSIONS}
    assert current_user_permissions(admin) == [ALL_PERMISSIONS]
    assert scope_for_role("admin") == "ALL"


def test_scope_for_roles() -> None:
    assert scope_for_role("student") == "SELF"
    assert scope_for_role("parent") == "CHILD"
    assert scope_for_role("teacher") == "CLASS"
    assert scope_for_role("school_admin") == "SCHOOL"
    assert current_user_scope(_user("student")) == "SELF"


def test_require_permission_allows_and_denies() -> None:
    dependency = require_permission("learn:practice:start")

    assert dependency(current=_user("student")) is not None

    with pytest.raises(HTTPException) as exc:
        dependency(current=_user("parent"))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "PERMISSION_DENIED"

    assert dependency(current=_user("admin")) is not None


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        (
            "guest",
            ["learn:content:read"],
            ["learn:kp:study", "learn:practice:start", "learn:exam:take"],
        ),
        (
            "student",
            ["learn:practice:submit", "learn:exam:take", "learn:wrong:self", "user:grade:change"],
            ["learn:stats:class:read", "learn:exam:grade", "content:publish", "family:control:write"],
        ),
        (
            "parent",
            ["learn:stats:child:read", "family:control:write", "family:report:read"],
            ["learn:exam:take", "learn:practice:start", "learn:exam:grade"],
        ),
        (
            "teacher",
            ["learn:stats:class:read", "learn:exam:grade", "learn:assignment:create"],
            ["learn:exam:take", "learn:wrong:self", "org:class:manage", "content:question:write"],
        ),
        (
            "head_teacher",
            ["org:class:manage", "learn:exam:grade", "learn:stats:class:read"],
            ["learn:exam:take", "admin:user:manage", "content:publish"],
        ),
        (
            "school_admin",
            ["org:teacher:assign", "admin:role:assign", "audit:log:read", "learn:exam:take"],
            ["system:config:write", "content:question:write", "content:review:decide"],
        ),
        (
            "content_operator",
            ["content:question:write", "content:publish", "content:kp:write"],
            ["content:review:decide", "learn:exam:take", "admin:role:assign"],
        ),
        (
            "auditor",
            ["content:review:decide", "audit:log:read", "admin:user:manage"],
            ["content:publish", "learn:exam:take", "system:config:write"],
        ),
        (
            "customer_service",
            ["support:ticket:manage", "admin:user:manage", "org:student:manage"],
            ["system:config:write", "content:question:write", "learn:exam:take"],
        ),
    ],
)
def test_permission_matrix_by_role(
    role: str, allowed: list[str], denied: list[str]
) -> None:
    user = _user(role)
    for permission in allowed:
        assert has_permission(user, permission), f"{role} 应具备 {permission}"
    for permission in denied:
        assert not has_permission(user, permission), f"{role} 不应具备 {permission}"


def test_super_admin_holds_all_permissions() -> None:
    admin = _user("super_admin")
    assert permissions_for_role("super_admin") == {ALL_PERMISSIONS}
    for permission in PERMISSIONS:
        assert has_permission(admin, permission)


def test_role_permission_catalog_is_consistent() -> None:
    catalog = set(PERMISSIONS) | {ALL_PERMISSIONS}
    for role, permissions in ROLE_PERMISSIONS.items():
        assert permissions <= catalog, role
        assert permissions, role


def test_permission_scope_catalog_is_valid() -> None:
    valid_scopes = {"NONE", "SELF", "CHILD", "CLASS", "SCHOOL", "ALL"}
    assert set(PERMISSIONS) == set(PERMISSION_SCOPE)
    for permission, scopes in PERMISSION_SCOPE.items():
        assert scopes, permission
        assert set(scopes) <= valid_scopes, permission


@pytest.mark.parametrize(
    ("role", "permission", "expected"),
    [
        ("guest", "learn:content:read", "NONE"),
        ("student", "learn:practice:start", "SELF"),
        ("student", "learn:stats:class:read", None),
        ("parent", "learn:stats:child:read", "CHILD"),
        ("parent", "learn:exam:report:self", "CHILD"),
        ("teacher", "learn:exam:grade", "CLASS"),
        ("teacher", "learn:exam:report:self", "CLASS"),
        ("school_admin", "learn:exam:report:self", "SCHOOL"),
        ("content_operator", "content:publish", "ALL"),
        ("auditor", "audit:log:read", "ALL"),
        ("super_admin", "system:config:write", "ALL"),
    ],
)
def test_scope_for_permission_matrix(role: str, permission: str, expected: str | None) -> None:
    assert scope_for_permission(role, permission) == expected
