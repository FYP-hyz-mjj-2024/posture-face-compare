# FastAPI server essentials
from typing import Union, cast
from fastapi import APIRouter, Depends, HTTPException
import uuid

# PostgreSQL database connection
from sqlalchemy.orm import Session

# Information Security
from passlib.context import CryptContext

# Locals
from database import get_db
from .models import User, GRANT_PERMISSION
from auth import generate_jwt, validate_user, send_verification_email
from .schemas import UserRegister, UserLoginWithEmail, UserLoginWithName


router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register/")
def register_user(user_register: UserRegister,
                  db: Session = Depends(get_db)):
    """
    Register a new user.
    :param user_register: User register schema class.
    :param db: Database object.
    :return: Registration result.
    """
    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.email == user_register.email)
    ).first()

    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    # Encrypt user password
    hashed_password = pwd_context.hash(user_register.password)

    # Create new user
    new_user = User(email=user_register.email, password_hash=hashed_password, name=user_register.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT token for email confirmation
    token = generate_jwt(new_user.id)

    # Send verification email
    send_verification_email(email_to=new_user.email, user_id=new_user.id, token=token)

    return {"msg": "User registered successfully. Please check your mailbox.", "user_id": str(new_user.id)}


@router.get("/verify_email/")
def verify_email(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    """
    New user email verification.
    :param user_id: UUID of the new user.
    :param token: JWT token of the user.
    :param db: Database object.
    :return: Verification result.
    """
    validate_user(user_id=user_id, token=token)

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.id == user_id)
    ).first()

    if not db_user or not isinstance(db_user, User):
        raise HTTPException(status_code=404, detail=f"Can't find user with id {str(user_id)}.")

    if db_user.is_verified:
        raise HTTPException(status_code=400, detail=f"Email already verified.")

    db_user.is_verified = True
    db.commit()

    return {"msg": "Email verified successfully."}


@router.post("/login/")
def login_user(user_login: Union[UserLoginWithEmail, UserLoginWithName],
               db: Session = Depends(get_db)):
    """
    Login existing user.
    :param user_login: User login schema class.
    :param db: Database object.
    :return: Login result.
    """

    if isinstance(user_login, UserLoginWithEmail):
        filter_condition = (User.email == user_login.email)
    elif isinstance(user_login, UserLoginWithName):
        filter_condition = (User.name == user_login.name)
    else:
        raise HTTPException(status_code=400, detail="(Dev) Invalid post parameters.")

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", filter_condition)
    ).first()

    # Password validation failed.
    if not db_user or not isinstance(db_user, User) or not pwd_context.verify(user_login.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password.")

    # Email verification.
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified.")

    # Certified user, hand out JWT token.
    token = generate_jwt(db_user.id)

    return {
        "msg": "Login successful",
        "user_id": str(db_user.id),
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/delete_account/")
def delete_user(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    """
    Delete existing user.
    :param user_id: UUID of the user.
    :param token: JWT token of the user.
    :param db: Database object.
    :return: Deletion result.
    """
    validate_user(user_id, token)

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.id == user_id)
    ).first()

    if not db_user or not isinstance(db_user, User):
        raise HTTPException(status_code=404, detail=f"User with id {user_id} is not found.")

    db.delete(db_user)
    db.commit()

    return {"msg": "User deleted successfully.", "user_id": str(user_id)}


@router.get("/get_user/")
def get_user(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    """
    Get information of a specific user.
    :param user_id: UUID of the user.
    :param token: JWT token of the user.
    :param db: Database object.
    :return: The information of the user.
    """
    validate_user(user_id, token)

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.id == user_id)
    ).first()

    if not db_user or not isinstance(db_user, User):
        raise HTTPException(status_code=404, detail=f"User with id {user_id} is not found.")

    return {
        "user_id": str(db_user.id),
        "created_at": str(db_user.created_at),
        "email": db_user.email,
        "name": db_user.name
    }


@router.post("/grant_user/")
def grant_permission(operator_user_id: uuid.UUID,
                     permission_applier_user_id: uuid.UUID,
                     token: str,
                     permission: int,
                     db: Session = Depends(get_db)):
    """
    The ability of a superuser to grant other user access.
    :param operator_user_id: The operator's user UUID.
    :param permission_applier_user_id: The permission applier's user UUID.
    :param token: The operator's JWT token.
    :param permission: Permission that the operator wants to grant.
    :param db: Database object.
    :return: Result of permission granting.
    """

    '''
    Operator
    '''
    validate_user(operator_user_id, token)

    db_operator_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.id == operator_user_id)
    ).first()

    # Operator not found.
    if not db_operator_user or not isinstance(db_operator_user, User):
        raise HTTPException(status_code=404, detail=f"Operator {permission_applier_user_id} is not found.")

    # Operator has no permission to grant other's access.
    if not db_operator_user.check_permission(permission=GRANT_PERMISSION):
        raise HTTPException(status_code=404, detail=f"Operator {permission_applier_user_id} "
                                                    f"is not allowed to grant permission.")

    '''
    Permission Applier
    '''
    db_permission_applier_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.id == permission_applier_user_id)
    ).first()

    # Permission Applier not found
    if not db_permission_applier_user or not isinstance(db_permission_applier_user, User):
        raise HTTPException(status_code=404, detail=f"User with id {permission_applier_user_id} is not found.")

    db_permission_applier_user.grant_permission(permission)
    db.commit()

    return {
        "msg": "Grant permission successful.",
        "user_id": str(permission_applier_user_id),
        "permission": permission,
    }



