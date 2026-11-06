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
    permissions_for_role,
    scope_for_role,
)
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
