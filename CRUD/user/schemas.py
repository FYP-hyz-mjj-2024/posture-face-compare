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


class WithUserId(BaseModel):
    user_id: uuid.UUID


class UserAuth(BaseModel):
    user_id: uuid.UUID
    token: str


class EmailVerifySuper(WithUserId):
    verify_user_id: uuid.UUID


class PermissionEdit(WithUserId):
    grant: bool
    requester_user_id: uuid.UUID
    permission: int


class UsersGet(WithUserId):
    range_from: int
    range_to: int


class UsersFindByName(WithUserId):
    query: str


class PasswordChange(WithUserId):
    requester_user_id: uuid.UUID
    new_password: str
