from uuid import UUID
from typing import Optional

# Local
from CRUD.user.schemas import UserAuth


class FaceUpload(UserAuth):
    blob: bytes
    description: Optional[str] = None


class FacesGet(UserAuth):
    range_from: int
    range_to: int


class FaceUpdate(UserAuth):
    face_id: UUID
    description: str


class FaceDelete(UserAuth):
    face_id: UUID


class FaceFindByID(UserAuth):
    face_id: UUID


class FacesFindByDesc(UserAuth):
    query: str


class FaceCompare(UserAuth):
    blob: bytes
