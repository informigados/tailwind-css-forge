from __future__ import annotations

from pydantic import BaseModel, Field


class PickDirectoryRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class PickDirectoryResponse(BaseModel):
    supported: bool
    path: str | None = None
