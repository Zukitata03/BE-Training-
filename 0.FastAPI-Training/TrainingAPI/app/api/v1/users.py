from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.security import RequireRole
from ...models.user import User
from ...schemas.user import RoleUpdate, UserListResponse, UserResponse
from ...services.user_service import UserService

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(RequireRole("admin")),
):
    service = UserService(db)
    users, total = await service.list_users(page, page_size)
    return UserListResponse(data=users, total=total, page=page, page_size=page_size)


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(RequireRole("admin")),
):
    service = UserService(db)
    user = await service.update_user_role(user_id, payload.role)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user