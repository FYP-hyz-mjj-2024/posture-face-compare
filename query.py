# FastAPI server essentials
from typing import cast, Optional
from fastapi import Depends, HTTPException, status, Header

# PostgreSQL database connection
from sqlalchemy.orm import Session

# Locals
from auth import validate_user
from database import get_db
from CRUD.user.models import User
from CRUD.user.schemas import WithUserId
from database import Base


def find_by(orm: Base,
            attr: str,
            val,
            fail_detail: Optional[str] = None,
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

    if fail_detail is None:
        fail_detail = f"{orm.__class__.__name__} with {attr} {str(val)} is not found."

    if not db_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=fail_detail)

    return db_orm


def _guard_db(auth: WithUserId, token, permission: int, db: Session):
    """
    Guard database from unauthorized operations.
    :param auth: Data objects with user authorization details, including user_id and token.
    :param permission: The target permission to check to allow this operation.
    :param db: Database session.
    :return: True if permission is granted. Otherwise, an exception will be raised.
    """
    # Check for user validation
    user_id = auth.user_id
    validate_user(user_id=user_id, token=token)

    db_uploader = find_by(orm=User,
                          attr="id",
                          val=user_id,
                          fail_detail=f"Failed to verify user {user_id}",
                          db=db)

    if not db_uploader.check_permission(permission=permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"The user {user_id} does not have the permission to access this resource.")

    return True


def get_header_token(authorization: str = Header(...)):
    """
    Get Bearer JWT authorization token from Authorization header.
    :param authorization: Authorization Header.
    :return: JWT token
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header.")

    if not authorization.startswith("Bearer"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format.")

    token = authorization[7:]

    return token
