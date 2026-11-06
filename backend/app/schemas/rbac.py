from typing import List, Optional

from pydantic import BaseModel, Field


class RolePermissionOut(BaseModel):
    code: str
    name: str
    level: str
    is_system: bool
    is_editable: bool
    user_count: int
    permissions: List[str]


class RoleListOut(BaseModel):
    items: List[RolePermissionOut]


class PermissionOut(BaseModel):
    code: str
    domain: str
    description: Optional[str] = None
    roles: List[str]


class PermissionListOut(BaseModel):
    domains: List[str]
    items: List[PermissionOut]


class RolePermissionsIn(BaseModel):
    permissions: List[str] = Field(default_factory=list, max_length=200)


class RolePermissionsOut(BaseModel):
    code: str
    permissions: List[str]
    added: List[str]
    removed: List[str]
