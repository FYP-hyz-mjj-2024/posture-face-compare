# Basic
import os
import time
import base64
from io import BytesIO
from typing import cast, Union
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
from CRUD.face.schemas import FaceUpload, FacesGet, FaceDelete, FaceFindByID, FaceFindByDesc, FaceCompare
from CRUD.user.models import User, WRITE, READ, DELETE
from CRUD.user.schemas import UserAuth
from auth import validate_user
from query import find_by

router = APIRouter()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Detect faces in an image.
face_detector = dlib.get_frontal_face_detector()

# Converts Image pixels to landmarks.
predictor = dlib.shape_predictor(os.path.join(os.path.dirname(__file__),
                                              "models",
                                              "shape_predictor_68_face_landmarks.dat"))

# Converts landmarks to feature.
face_rec_model = dlib.face_recognition_model_v1(os.path.join(os.path.dirname(__file__),
                                                             "models",
                                                             "dlib_face_recognition_resnet_model_v1.dat"))

cached_faces = []


def retrieve_face_feature(blob):
    """
    Retrieve face features from a blob. If there's no face in the image, return none.
    Each face is represented by a feature of a length-128 vector.
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

    # Adaptive Histogram Equalization: Detect performance under low resolution.
    image_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(image_gray)

    # Retrieve faces
    faces = face_detector(image_gray, upsample_num_times=2)

    if len(faces) == 0:
        return None

    # Use the most significant face.
    face = faces[0]

    # Face landmarks.
    landmarks = predictor(image_gray, face)
    face_feature = face_rec_model.compute_face_descriptor(image, landmarks)

    return list(face_feature)


def compare_faces(feature_1, feature_2) -> float:
    """
    Calculate the inverse Euclidean distance of two face features,
    each being a 128-dimensional vector.
    :param feature_1: First feature.
    :param feature_2: Second feature.
    :return: The inverse Euclidean distance as a similarity score.
    """
    f1, f2 = np.array(feature_1), np.array(feature_2)
    score = 1 / (np.linalg.norm(f1 - f2) + np.finfo(np.float32).eps)
    return float(score)


def _guard_db(auth: UserAuth, permission: int, db: Session):
    """
    Guard database from unauthorized operations.
    :param auth: Data objects with user authorization details, including user_id and token.
    :param permission: The target permission to check to allow this operation.
    :param db: Database session.
    :return: True if permission is granted. Otherwise, an exception will be raised.
    """
    # Check for user validation.
    uploader_id = auth.user_id
    uploader_token = auth.token
    validate_user(user_id=uploader_id, token=uploader_token)

    db_uploader = find_by(orm=User,
                          attr="id",
                          val=uploader_id,
                          fail_detail=f"Failed to verify user {uploader_id}",
                          db=db)

    if not db_uploader.check_permission(permission=permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"The user {uploader_id} does not have the permission to access this resource.")

    return True


def _check_file_type(blob: bytes, allowed_types):
    """
    Check for file types from the blob.
    :param blob: The base64 string of the target file.
    :param allowed_types: A list of allowed types.
    :return: True if file type is valid. Otherwise, an exception will be raised.
    """
    try:
        file_data = base64.b64decode(blob)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Decode base64 data error: Unable to decode.")

    mime_type = magic.from_buffer(file_data, mime=True)
    file_ext = mime_type.split("/")[-1]

    if file_ext not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unsupported file type: {file_ext}.")

    return True


@router.post("/upload_face/")
def upload_face(face_upload: FaceUpload, db: Session = Depends(get_db)):
    """
    Upload a face.
    :param face_upload: Face upload data.
    :param db: Database session.
    :return: Upload message.
    """

    _guard_db(auth=face_upload, permission=WRITE, db=db)
    _check_file_type(blob=face_upload.blob, allowed_types=ALLOWED_EXTENSIONS)

    face_feature = retrieve_face_feature(face_upload.blob)

    if face_feature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No face detected, therefore the image is not saved.")

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


@router.post("/get_faces/")
def get_faces(faces_get: FacesGet, db: Session = Depends(get_db)):
    """
    Get faces from a given range.
    :param faces_get: Faces get data.
    :param db: Database Session.
    :return:
    """
    _guard_db(auth=faces_get, permission=READ, db=db)

    # Process the query range.
    _limit = faces_get.range_to - faces_get.range_from + 1
    if _limit < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid range. The \"to\" should be greater than the \"from\".")
    _offset = faces_get.range_from

    total_num = db.query(Face).count()

    db_faces = db.query(Face).offset(_offset).limit(_limit).all()

    return {
        "num_total": total_num,
        "num_this_page": len(db_faces),   # In case limit is over total data num.
        "faces": db_faces
    }


@router.post("/delete_face/")
def delete_face(face_delete: FaceDelete, db: Session = Depends(get_db)):
    """
    Delete a specific face.
    :param face_delete: Face delete data.
    :param db: Database Session.
    :return: A successful message if deleted successful. Otherwise an error will be raised.
    """
    _guard_db(auth=face_delete, permission=DELETE, db=db)

    db_face = db.query(Face).filter(
        cast("ColumnElement[bool]", Face.id == face_delete.face_id)
        ).first()

    if db_face is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"The face with id {face_delete.face_id} does not exist."
                                   f"It is possible that the face has already been deleted.")

    db.delete(db_face)
    db.commit()

    return {"msg": f"Face with ID {face_delete.face_id} has been deleted."}


@router.post("/compare_face/")
def compare_face(face_compare: FaceCompare, db: Session = Depends(get_db)):
    """
    Upload a face and find its match.
    :param face_compare: Face blob to upload.
    :param db: Database session.
    :return: A list of matched faces' descriptions with scores.
    """

    _guard_db(auth=face_compare, permission=WRITE, db=db)
    _check_file_type(blob=face_compare.blob, allowed_types=ALLOWED_EXTENSIONS)

    face_feature = retrieve_face_feature(face_compare.blob)

    if face_feature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No face detected, therefore this image can't be compared.")

    _t_start = time.time()

    global cached_faces
    if len(cached_faces) == 0:
        db_faces = db.query(Face).all()
        cached_faces = [(db_face.description, db_face.feature) for db_face in db_faces]

    # desc_scores = [(cached_feature[0], compare_faces(face_feature, cached_feature[1]))
    #                for cached_feature in cached_faces]

    desc_scores = [{
        "description": cached_face[0],
        "score": compare_faces(face_feature, cached_face[1]),
    } for cached_face in cached_faces]

    desc_scores = sorted(desc_scores, key=lambda obj: obj["score"], reverse=True)

    _t_query = time.time() - _t_start

    return {
        "desc_scores": desc_scores,
        "query_time": _t_query
    }


@router.post("/find_face")
def find_face(face_find: Union[FaceFindByID, FaceFindByDesc], db: Session = Depends(get_db)):
    """
    Find a specific face using face_id or description.
    :param face_find: Face find data.
    :param db: Database session.
    :return: If success, returns the found face. Otherwise, an HTTP exception will be raised.
    """
    _guard_db(auth=face_find, permission=WRITE, db=db)

    if isinstance(face_find, FaceFindByID):
        attr = "id"
    elif isinstance(face_find, FaceFindByDesc):
        attr = "description"
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unprocessable entity.")

    db_face = find_by(orm=Face, attr=attr, val=getattr(face_find, attr),
                      fail_detail=f"No result for this query.", db=db)

    return {
        "face": db_face
    }
