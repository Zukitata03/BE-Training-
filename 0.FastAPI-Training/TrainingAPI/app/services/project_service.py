from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project import Project, ProjectStatus
from ..schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_projects(
        self, owner_id: int, page: int = 1, page_size: int = 20
    ) -> tuple[list[Project], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count()).select_from(Project).where(Project.owner_id == owner_id)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        projects = list(result.scalars().all())
        return projects, total

    async def get_project(self, project_id: int, owner_id: int) -> Project | None:
        stmt = select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_project(self, payload: ProjectCreate, owner_id: int) -> ProjectResponse:
        project = Project(
            name=payload.name,
            description=payload.description,
            owner_id=owner_id,
            status=payload.status,
        )
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        return ProjectResponse.model_validate(project)

    async def update_project(
        self, project_id: int, owner_id: int, payload: ProjectUpdate
    ) -> Project | None:
        project = await self.get_project(project_id, owner_id)
        if project is None:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int, owner_id: int) -> bool:
        project = await self.get_project(project_id, owner_id)
        if project is None:
            return False
        await self.db.delete(project)
        await self.db.flush()
        return True
