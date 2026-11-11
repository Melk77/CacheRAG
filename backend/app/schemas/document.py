
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict



class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    collection_id: uuid.UUID
    filename: str
    file_type: str
    status: str
    file_size: int
    page_count: int
    chunk_count: int
    error_message: str | None
    uploaded_at: datetime
    processed_at: datetime | None
