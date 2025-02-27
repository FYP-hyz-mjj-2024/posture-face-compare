# FastAPI server essentials
from typing import Union, cast, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
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


def _find_user_by(attr: str,
                  val,
                  fail_detail: str = "User not found.",
                  db: Session = Depends()):
    """
    Find user by its attribute. Equivalent to:

    ``SELECT * FROM users WHERE attr = val;``

    :param attr: The column attribute, should be unique.
    :param val: The match value of the attribute.
    :param db: Database Session.
    :return: The matched user. Otherwise, returns 404.
    """
    column = getattr(User, attr, None)
    if column is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Invalid attribute access of {attr}.")

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", column == val)
    ).first()

    if not db_user or not isinstance(db_user, User):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=fail_detail)

    return db_user


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

    db_user = _find_user_by(attr="id",
                            val=user_id,
                            fail_detail=f"User with id {user_id} is not found.",
                            db=db)

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

    db_user = _find_user_by(attr="id",
                            val=user_id,
                            fail_detail=f"User with id {user_id} is not found.",
                            db=db)

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

    db_user = _find_user_by(attr="id",
                            val=user_id,
                            fail_detail=f"User with id {user_id} is not found.",
                            db=db)

    return {
        "user_id": str(db_user.id),
        "created_at": str(db_user.created_at),
        "email": db_user.email,
        "name": db_user.name
    }


@router.post("/get_users/")
def get_users(query: str = "", db: Session = Depends(get_db)):
    """
    Get a list of users with a search query. If the query is not given,
    all users are returned, i.e., matches the empty query.
    :param query: The search query.
    :param db: Database object.
    :return: A list of users that matches the query.
    """

    db_users = db.query(User).filter(User.name.like(f"%{query}%")).all()

    return db_users


@router.post("/grant_user/")
def grant_permission(operator_user_id: uuid.UUID,
                     requester_user_id: uuid.UUID,
                     token: str,
                     permission: int,
                     db: Session = Depends(get_db)):
    """
    The ability of a superuser to grant other user access.
    :param operator_user_id: The operator's user UUID.
    :param requester_user_id: The permission applier's user UUID.
    :param token: The operator's JWT token.
    :param permission: Permission that the operator wants to grant.
    :param db: Database object.
    :return: Result of permission granting.
    """

    '''
    Operator
    '''
    validate_user(operator_user_id, token)

    db_operator_user = _find_user_by(attr="id",
                                     val=operator_user_id,
                                     fail_detail=f"Operator {operator_user_id} not found.",
                                     db=db)

    # Operator has no permission to grant other's access.
    if not db_operator_user.check_permission(permission=GRANT_PERMISSION):
        raise HTTPException(status_code=403, detail=f"Operator {requester_user_id} "
                                                    f"is not allowed to grant permission.")

    '''
    Permission Applier
    '''
    db_requester_user = _find_user_by(attr="id",
                                      val=requester_user_id,
                                      fail_detail=f"Requestor {requester_user_id} not found.",
                                      db=db)

    db_requester_user.grant_permission(permission)
    db.commit()

    return {
        "msg": "Grant permission successful.",
        "user_id": str(requester_user_id),
        "permission": permission,
    }



