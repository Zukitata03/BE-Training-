from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from .user import User
from .book import Book
from .blockchain_event import BlockchainEvent
from .project import Project

__all__ = ["Base", "User", "Book", "BlockchainEvent", "Project"]
