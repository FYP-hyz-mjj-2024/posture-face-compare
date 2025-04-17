from uuid import UUID
from typing import Optional

# Local
from CRUD.user.schemas import WithUserId


class FaceUpload(WithUserId):
    blob: bytes
    description: Optional[str] = None


class FacesGet(WithUserId):
    range_from: int
    range_to: int


class FaceUpdate(WithUserId):
    face_id: UUID
    description: str


class FaceDelete(WithUserId):
    face_id: UUID


class FaceFindByID(WithUserId):
    face_id: UUID


class FacesFindByDesc(WithUserId):
    query: str


class FaceCompare(WithUserId):
    blob: bytes
