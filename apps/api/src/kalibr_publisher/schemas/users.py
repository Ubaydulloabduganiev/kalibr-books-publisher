"""Request and response models for account management."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)
    role: str = Field(default="editor", pattern="^(admin|editor)$")


class PasswordChange(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    created_at: str
    updated_at: str


class UserList(BaseModel):
    count: int
    users: list[UserOut]
