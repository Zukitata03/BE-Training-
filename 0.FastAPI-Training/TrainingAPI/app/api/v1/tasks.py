from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status

from ...tasks.celery_app import celery_app

router = APIRouter()


@router.get("/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    try:
        result: AsyncResult = celery_app.AsyncResult(task_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task backend unavailable",
        ) from exc

    if result.ready():
        if result.successful():
            return {"status": "completed", "result": result.result}
        return {"status": "failed", "error": str(result.result)}

    return {"status": "processing"}

