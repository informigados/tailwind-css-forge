from __future__ import annotations

from fastapi import APIRouter

from app.schemas.system import PickDirectoryRequest, PickDirectoryResponse
from app.utils.native_dialog import pick_directory


router = APIRouter(tags=["system"])


@router.post("/system/pick-directory", response_model=PickDirectoryResponse)
def open_directory_picker(payload: PickDirectoryRequest) -> PickDirectoryResponse:
    supported, selected_path = pick_directory(payload.title)
    return PickDirectoryResponse(supported=supported, path=selected_path)
