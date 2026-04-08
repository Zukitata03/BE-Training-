from fastapi import APIRouter

from . import auth, blockchain, books, projects, tasks, users

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(books.router, prefix="/books", tags=["books"])
router.include_router(blockchain.router, prefix="/blockchain", tags=["blockchain"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
