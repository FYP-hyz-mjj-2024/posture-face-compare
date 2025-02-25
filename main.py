from typing import Union, cast
from fastapi import FastAPI, Depends, HTTPException
import uvicorn

from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from passlib.context import CryptContext

# Locals
from database import get_db
from models import User     # Local model

app = FastAPI()

# Password Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRegister(BaseModel):
    email: str
    password: str
    name: str


class UserLoginWithEmail(BaseModel):
    email: str
    password: str


class UserLoginWithName(BaseModel):
    name: str
    password: str


# Router: User Register
@app.post("/register/")
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

    return {"msg": "User registered successfully.", "user_id": new_user.id}


@app.post("/login/")
def login_user(user_login: Union[UserLoginWithEmail, UserLoginWithName],
               db: Session = Depends(get_db)):

    if isinstance(user_login, UserLoginWithEmail):
        filter_condition = (User.email == user_login.email)
    elif isinstance(user_login, UserLoginWithName):
        filter_condition = (User.name == user_login.name)
    else:
        raise HTTPException(status_code=400, detail="Wrong ")

    db_user = db.query(User).filter(
        cast("ColumnElement[bool]", filter_condition)
    ).first()

    if not db_user or not pwd_context.verify(user_login.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return {"msg": "Login successful", "user_id": db_user.id}


# @app.get("/")
# def read_root():
#     return {"Hello": "World"}
#
#
# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)