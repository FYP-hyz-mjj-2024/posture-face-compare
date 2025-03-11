# FastAPI server essentials
from typing import Union, cast, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import uuid

# PostgreSQL database connection
from sqlalchemy.orm import Session

# Information Security
from passlib.context import CryptContext

# Locals
from auth import generate_jwt, validate_user, send_verification_email
from database import get_db
from CRUD.user.models import User, GRANT_PERMISSION
from CRUD.user.schemas import UserAuth, UserRegister, UserLoginWithEmail, UserLoginWithName
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
