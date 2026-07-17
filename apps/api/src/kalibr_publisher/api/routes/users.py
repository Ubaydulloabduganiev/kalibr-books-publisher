"""Admin-managed account endpoints: create, list, change password, delete."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from kalibr_publisher.api.deps import require_internal_api_key
from kalibr_publisher.core.errors import ApiError
from kalibr_publisher.core.users import (
    create_user,
    delete_user,
    get_user,
    list_users,
    update_password,
)
from kalibr_publisher.schemas.users import PasswordChange, UserCreate, UserList, UserOut

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_internal_api_key)],
)


def _public(user: object) -> UserOut:
    return UserOut(**user.to_public_dict())  # type: ignore[attr-defined]


@router.get("", response_model=UserList)
async def list_accounts() -> UserList:
    users = list_users()
    return UserList(count=len(users), users=[_public(user) for user in users])


@router.post("", response_model=UserOut, status_code=201)
async def create_account(payload: UserCreate) -> UserOut:
    try:
        user = create_user(
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name or "",
            role=payload.role,
        )
    except ValueError as exc:
        raise ApiError(
            status_code=422,
            code="invalid_account",
            message=str(exc),
            recovery_suggestion="Provide a unique username and a password of at least 8 characters.",
        ) from exc
    logger.info("account_created", username=user.username, role=user.role)
    return _public(user)


@router.post("/{user_id}/password", response_model=UserOut)
async def change_password(user_id: str, payload: PasswordChange) -> UserOut:
    user = get_user(user_id)
    if user is None:
        raise ApiError(
            status_code=404,
            code="user_not_found",
            message="The requested account does not exist.",
            recovery_suggestion="Refresh the account list and try again.",
        )
    try:
        user = update_password(user_id, payload.new_password)
    except ValueError as exc:
        raise ApiError(
            status_code=422,
            code="invalid_password",
            message=str(exc),
            recovery_suggestion="Use a password of at least 8 characters.",
        ) from exc
    logger.info("password_changed", username=user.username)
    return _public(user)


@router.delete("/{user_id}", status_code=204)
async def remove_account(user_id: str) -> None:
    if not delete_user(user_id):
        raise ApiError(
            status_code=404,
            code="user_not_found",
            message="The requested account does not exist.",
            recovery_suggestion="Refresh the account list and try again.",
        )
    logger.info("account_deleted", user_id=user_id)
