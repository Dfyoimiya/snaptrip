"""Schemas for Menu, Resource, Role, Admin management.

Author: SnapTrip Team
Date: 2026-06-09
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ===== Menu =====

class MenuNode(BaseModel):
    id: UUID
    parent_id: UUID | None = None
    title: str
    name: str | None = None
    icon: str | None = None
    sort: int = 0
    hidden: int = 0
    level: int = 0
    children: list["MenuNode"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class MenuCreate(BaseModel):
    parent_id: UUID | None = None
    title: str
    name: str | None = None
    icon: str | None = None
    sort: int = 0
    hidden: int = 0
    level: int = 0


class MenuUpdate(BaseModel):
    parent_id: UUID | None = None
    title: str | None = None
    name: str | None = None
    icon: str | None = None
    sort: int | None = None
    hidden: int | None = None
    level: int | None = None


# ===== Resource =====

class ResourceCategoryResponse(BaseModel):
    id: UUID
    name: str
    sort: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResourceCategoryCreate(BaseModel):
    name: str
    sort: int = 0


class ResourceCategoryUpdate(BaseModel):
    name: str | None = None
    sort: int | None = None


class ResourceResponse(BaseModel):
    id: UUID
    category_id: UUID | None = None
    name: str
    url: str | None = None
    description: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResourceCreate(BaseModel):
    category_id: UUID | None = None
    name: str
    url: str | None = None
    description: str | None = None


class ResourceUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = None
    url: str | None = None
    description: str | None = None


# ===== Role =====

class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    status: int = 1
    sort: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str | None = None
    status: int = 1
    sort: int = 0


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: int | None = None
    sort: int | None = None


class RoleStatusUpdate(BaseModel):
    status: int


class AllocMenuRequest(BaseModel):
    role_id: UUID
    menu_ids: list[UUID]


class AllocResourceRequest(BaseModel):
    role_id: UUID
    resource_ids: list[UUID]


# ===== Admin User =====

class AdminUserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime | None = None
    roles: list[RoleResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AdminRegisterRequest(BaseModel):
    email: str
    password: str
    role_ids: list[UUID] = Field(default_factory=list)


class AdminUpdateRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None
    role_ids: list[UUID] | None = None


class AdminRoleUpdateRequest(BaseModel):
    admin_id: UUID
    role_ids: list[UUID]
