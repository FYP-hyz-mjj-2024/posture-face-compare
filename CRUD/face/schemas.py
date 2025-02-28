from uuid import UUID
from typing import Optional

# Local
from CRUD.user.schemas import UserAuth


class FaceUpload(UserAuth):
    blob: bytes
    description: Optional[str] = None
