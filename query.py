# FastAPI server essentials
from typing import cast
from fastapi import  Depends, HTTPException, status

# PostgreSQL database connection
from sqlalchemy.orm import Session

# Locals
from auth import validate_user
from database import get_db
from CRUD.user.models import User
from CRUD.user.schemas import UserAuth
from database import Base


def find_by(orm: Base,
            attr: str,
            val,
            fail_detail: str = "User not found.",
            db: Session = Depends(get_db)) -> Base:
    """
    Find an orm object by its attribute. Equivalent to:

    ``SELECT * FROM <orm> WHERE <attr> = <val>;``

    :param orm: ORM object to find.
    :param attr: The column attribute, should be unique.
    :param val: The match value of the attribute.
    :param fail_detail: The error message to display when find user failed.
    :param db: Database Session.
    :return: The matched user. Otherwise, returns 404.
    """

    # This orm object doesn't have this attribute.
    column = getattr(orm, attr, None)
    if column is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Invalid attribute access of {attr}.")

    db_orm = db.query(orm).filter(
        cast("ColumnElement[bool]", column == val)
    ).first()

    if not db_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=fail_detail)

    return db_orm


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
