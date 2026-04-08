from fastapi import FastAPI

from .api.v1.router import router as api_router
from .core.database import close_db, init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="Training API",
        description="Production-quality FastAPI training platform.",
    )

    @app.on_event("startup")
    async def startup():
        await init_db()

    @app.on_event("shutdown")
    async def shutdown():
        await close_db()

    app.include_router(api_router, prefix="/api/v1")
    return app
