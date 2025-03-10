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


class FaceDelete(UserAuth):
    face_id: UUID
