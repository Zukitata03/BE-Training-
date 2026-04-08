from datetime import datetime

from pydantic import BaseModel

from ..models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    status: ProjectStatus = ProjectStatus.active


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
