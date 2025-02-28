# FastAPI server essentials
from fastapi import APIRouter, Depends, HTTPException, status

# PostgreSQL database connection
from sqlalchemy.orm import Session


# Locals
from database import get_db
from CRUD.face.models import Face
from CRUD.face.schemas import FaceUpload
from CRUD.user.models import WRITE
from CRUD.user.services import find_user_by
from auth import validate_user


router = APIRouter()


@router.post("/upload_face/")
def upload_face(face_upload: FaceUpload, db: Session = Depends(get_db)):
    """
    Upload a face.
    :param face_upload: Face image file to upload.
    :param db: Database session.
    :return: Upload message.
    """
    uploader_id = face_upload.user_id
    uploader_token = face_upload.token

    validate_user(user_id=uploader_id, token=uploader_token)

    db_uploader = find_user_by(attr="id",
                               val=uploader_id,
                               fail_detail=f"Upload Face Failed: Can't find uploader {uploader_id}",
                               db=db)

    if not db_uploader.check_permission(permission=WRITE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"The user {uploader_id} does not have the permission to upload face.")

    new_face = Face(
        uploaded_by=face_upload.user_id,
        blob=face_upload.blob,
        description=face_upload.description
    )

    db.add(new_face)
    db.commit()
    db.refresh(new_face)

    return {
        "face_id": new_face.id,
        "uploaded_at": new_face.uploaded_at,
        "uploaded_by": new_face.uploaded_by,
        "description": new_face.description
    }
