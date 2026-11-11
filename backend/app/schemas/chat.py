
from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    web_search_enabled: bool = False


class SourceResponse(BaseModel):
    source_type: Literal["document", "web"] = "document"

    document_id: str | None = None
    filename: str | None = None
    page_number: int | None = None

    title: str | None = None
    url: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
