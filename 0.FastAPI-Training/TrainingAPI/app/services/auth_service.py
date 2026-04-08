from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import hash_password, verify_password
from ..models.user import User, UserRole
from ..schemas.user import UserCreate, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, payload: UserCreate) -> UserResponse:
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=UserRole.USER,
        )
        self.db.add(user)
        try:
            await self.db.flush()
            await self.db.refresh(user)
        except IntegrityError as exc:
            raise ValueError(f"Email {payload.email} already registered") from exc
        return UserResponse.model_validate(user)

    async def authenticate_user(self, email: str, password: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
