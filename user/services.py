# FastAPI server essentials
from typing import Union, cast
from fastapi import APIRouter, Depends, HTTPException, Header, status
import uuid

# PostgreSQL database connection
from sqlalchemy.orm import Session

# Information Security
from passlib.context import CryptContext

# Locals
from database import get_db
from .models import User     # Local model
from auth import generate_jwt, validate_user
from .schemas import UserRegister, UserLoginWithEmail, UserLoginWithName


router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register/")
def register_user(user_register: UserRegister,
                  db: Session = Depends(get_db)):
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

    return {"msg": "User registered successfully.", "user_id": str(new_user.id)}


@router.post("/login/")
def login_user(user_login: Union[UserLoginWithEmail, UserLoginWithName],
               db: Session = Depends(get_db)):

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
    if not db_user or not pwd_context.verify(user_login.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password.")

    # Certified user, hand out JWT token.
    token = generate_jwt(db_user.id)

    return {
        "msg": "Login successful",
        "user_id": str(db_user.id),
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/delete_user/")
def delete_user(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    validate_user(user_id, token)

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.id == user_id)
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} is not found.")

    db.delete(db_user)
    db.commit()

    return {"msg": "User deleted successfully.", "user_id": str(user_id)}


@router.get("/get_user/")
def get_user(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    validate_user(user_id, token)

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", User.id == user_id)
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} is not found.")

    return {
        "user_id": str(db_user.id),
        "email": db_user.email,
        "name": db_user.name
    }



