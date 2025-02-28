# Basic
import os
import base64
from io import BytesIO
from PIL import Image
import dlib
import numpy as np
import cv2
import magic

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

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

face_detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(os.path.join(os.path.dirname(__file__),
                                              "models",
                                              "shape_predictor_68_face_landmarks.dat"))

face_rec_model = dlib.face_recognition_model_v1(os.path.join(os.path.dirname(__file__),
                                                             "models",
                                                             "dlib_face_recognition_resnet_model_v1.dat"))


def retrieve_face_feature(blob):
    """
    Retrieve face features from a blob. If there's no face in the image, return none.
    :param blob: Blob, base64 of an image.
    :return: The face feature of the first discovered face in the image,
             if this image contains any faces. Otherwise, None.
    """

    # Retrieve image file from base64.
    file_data = base64.b64decode(blob)
    _image = Image.open(BytesIO(file_data))

    # Convert to dlib-readable format.
    image = np.array(_image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Retrieve faces
    faces = face_detector(image_gray)

    if len(faces) == 0:
        return None

    # Use the most significant face.
    face = faces[0]

    # Face landmarks.
    landmarks = predictor(image_gray, face)
    face_feature = face_rec_model.compute_face_descriptor(image, landmarks)

    return list(face_feature)


def compare_faces(feature_1, feature_2) -> float:
    f1, f2 = np.array(feature_1), np.array(feature_2)
    # norm_1, norm_2 = np.linalg.norm(f1), np.linalg.norm(f2)
    # if norm_1 == 0 or norm_2 == 0:
    #     return 0.0
    #
    # dot_prod = np.dot(f1, f2.T)
    # _score = dot_prod / (norm_1 * norm_2)
    # score = 0.5 * (_score + 1)

    score = 1 / (np.linalg.norm(f1 - f2) + np.finfo(np.float32).eps)
    return float(score)


def _guard_face_db(face_upload: FaceUpload, db: Session):
    """
    Check for user permission and uploaded file types.
    :param face_upload: FaceUpload schema object.
    :param db: Database session.
    :return:
    """
    # Check for user validation.
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

    # Check for file types.
    try:
        file_data = base64.b64decode(face_upload.blob)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Decode base64 data error: Unable to decode.")

    mime_type = magic.from_buffer(file_data, mime=True)
    file_ext = mime_type.split("/")[-1]

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unsupported file type: {file_ext}.")

    return True


@router.post("/upload_face/")
def upload_face(face_upload: FaceUpload, db: Session = Depends(get_db)):
    """
    Upload a face.
    :param face_upload: Face image file to upload.
    :param db: Database session.
    :return: Upload message.
    """

    _guard_face_db(face_upload=face_upload, db=db)

    face_feature = retrieve_face_feature(face_upload.blob)

    if face_feature is None:
        return {
            "msg": "No face detected, therefore the image is not saved."
        }

    new_face = Face(
        uploaded_by=face_upload.user_id,
        blob=face_upload.blob,
        description=face_upload.description,
        feature=face_feature
    )

    db.add(new_face)
    db.commit()
    db.refresh(new_face)

    return {
        "face_id": new_face.id,
        "uploaded_at": new_face.uploaded_at,
        "uploaded_by": new_face.uploaded_by,
        "description": new_face.description,
    }


@router.post("/find_face/")
def find_face(face_upload: FaceUpload, db: Session = Depends(get_db)):
    """
    Upload a face and find its match.
    :param face_upload: Face blob to upload.
    :param db: Database session.
    :return: A list of matched faces' descriptions with scores.
    """
    _guard_face_db(face_upload=face_upload, db=db)

    face_feature = retrieve_face_feature(face_upload.blob)

    if face_feature is None:
        return {
            "msg": "No face detected, therefore the image is not saved."
        }

    db_faces = db.query(Face).all()
    descriptions = [db_face.description for db_face in db_faces]
    scores = [compare_faces(face_feature, db_face.feature) for db_face in db_faces]

    return {
        "features": sorted([(desc, score) for desc, score in zip(descriptions, scores)],
                           key=lambda obj: obj[1],
                           reverse=True)
    }
