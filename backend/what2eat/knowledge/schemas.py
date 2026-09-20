from enum import StrEnum
from pathlib import Path
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentState(StrEnum):
    pending = 'pending'
    indexing = 'indexing'
    ready = 'ready'
    failed = 'failed'
    deleting = 'deleting'


class DocumentCreate(BaseModel):
    id: UUID
    content_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_path: str
    source_url: str | None = None
    title: str
    category: str = '用户资料'
    index_version: str
    metadata: dict = Field(default_factory=dict)


class DocumentContent(BaseModel):
    id: UUID
    title: str
    format: str
    content: str
    source_url: str | None = None
