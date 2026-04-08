from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.security import get_current_active_user
from ...dependencies.pagination import PaginationParams
from ...models.user import User
from ...schemas.book import BookCreate, BookResponse, BookUpdate
from ...schemas.common import ErrorResponse, PaginatedResponse
from ...services.book_service import BookService
from ...services.notification_service import log_new_book_created
from ...tasks.celery_app import celery_app

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[BookResponse])
async def get_books(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BookService(db)
    books, total = await service.get_books(
        user_id=current_user.id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return PaginatedResponse(
        data=[BookResponse.model_validate(b) for b in books],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    payload: BookCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BookService(db)
    created = await service.create_book(payload, owner_id=current_user.id)
    background_tasks.add_task(log_new_book_created, created.title, current_user.id)
    return created


@router.post("/{book_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_book_owner_activity(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BookService(db)
    book = await service.get_book(book_id=book_id, user_id=current_user.id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    try:
        async_result = celery_app.send_task(
            "TrainingAPI.app.tasks.user_activity_tasks.analyze_user_activity",
            args=[current_user.id],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue unavailable",
        ) from exc
    return {"task_id": async_result.id, "status": "processing"}


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BookService(db)
    book = await service.get_book(book_id, user_id=current_user.id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return BookResponse.model_validate(book)


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    payload: BookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BookService(db)
    book = await service.update_book(book_id, owner_id=current_user.id, payload=payload)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return BookResponse.model_validate(book)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BookService(db)
    deleted = await service.delete_book(book_id, owner_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
