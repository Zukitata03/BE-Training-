from pydantic import BaseModel


class BookCreate(BaseModel):
    title: str
    author: str
    description: str | None = None


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    description: str | None = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    description: str | None
    owner_id: int

    model_config = {"from_attributes": True}
