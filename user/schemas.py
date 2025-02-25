from pydantic import BaseModel


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
