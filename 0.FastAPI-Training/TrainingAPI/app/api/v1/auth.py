from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.security import OAuth2PasswordRequestForm
from ...core.database import get_db
from ...core.security import create_access_token, create_refresh_token, decode_token
from ...schemas.user import Token, TokenRefresh, UserCreate, UserLogin
from ...services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidPasswordError,
)
from ...services.notification_service import log_new_user_registered

router = APIRouter()


@router.post("/register", response_model=None, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        await service.register_user(payload)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    background_tasks.add_task(log_new_user_registered, payload.email)
    return {"message": "User registered successfully"}


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    user = await service.authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access = create_access_token(data={"sub": user.email})
    refresh = create_refresh_token(data={"sub": user.email})
    return Token(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=Token)
async def refresh_token(payload: UserLogin):
    token_data = decode_token(payload.password)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    email = token_data.get("sub")
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    access = create_access_token(data={"sub": email})
    new_refresh = create_refresh_token(data={"sub": email})
    return Token(access_token=access, refresh_token=new_refresh)
