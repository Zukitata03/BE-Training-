from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.book import Book
from ..schemas.book import BookCreate, BookResponse, BookUpdate


class BookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_books(self, user_id: int, page: int = 1, page_size: int = 20) -> tuple[list[Book], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count()).select_from(Book).where(Book.owner_id == user_id)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Book)
            .where(Book.owner_id == user_id)
            .order_by(Book.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        books = list(result.scalars().all())
        return books, total

    async def get_book(self, book_id: int, user_id: int) -> Book | None:
        stmt = select(Book).where(Book.id == book_id, Book.owner_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_book(self, payload: BookCreate, owner_id: int) -> BookResponse:
        book = Book(
            title=payload.title,
            author=payload.author,
            description=payload.description,
            owner_id=owner_id,
        )
        self.db.add(book)
        await self.db.flush()
        await self.db.refresh(book)
        return BookResponse.model_validate(book)

    async def update_book(self, book_id: int, owner_id: int, payload: BookUpdate) -> Book | None:
        book = await self.get_book(book_id, owner_id)
        if book is None:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(book, field, value)
        await self.db.flush()
        await self.db.refresh(book)
        return book

    async def delete_book(self, book_id: int, owner_id: int) -> bool:
        book = await self.get_book(book_id, owner_id)
        if book is None:
            return False
        await self.db.delete(book)
        await self.db.flush()
        return True
