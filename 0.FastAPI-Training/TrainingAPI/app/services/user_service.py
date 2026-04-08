from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User, UserRole
from ..schemas.user import UserResponse


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self, page: int = 1, page_size: int = 20) -> tuple[list[UserResponse], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count()).select_from(User)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        users = list(result.scalars().all())
        return [UserResponse.model_validate(u) for u in users], total

    async def get_user_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user_role(self, user_id: int, new_role: UserRole) -> UserResponse | None:
        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        user.role = new_role
        await self.db.flush()
        await self.db.refresh(user)
        return UserResponse.model_validate(user)