from pydantic import BaseModel
import uuid


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


class UserAuth(BaseModel):
    user_id: uuid.UUID
    token: str
