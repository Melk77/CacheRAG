import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = ""


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    version: int
    created_at: datetime
    updated_at: datetime

class CollectionListResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    version: int
    created_at: datetime
    updated_at: datetime
    document_count: int

class CollectionRename(BaseModel):
    name: str = Field(min_length=1, max_length=150)