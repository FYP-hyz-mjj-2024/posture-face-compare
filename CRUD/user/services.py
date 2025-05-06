# FastAPI server essentials
from typing import Union, cast
from fastapi import APIRouter, Depends, HTTPException, status
import uuid

# PostgreSQL database connection
from sqlalchemy import desc
from sqlalchemy.orm import Session

# Information Security
from passlib.context import CryptContext

# Locals
from auth import generate_jwt, validate_user
from database import get_db
from CRUD.user.models import User, READ, GRANT_PERMISSION
from CRUD.user.schemas import (
    WithUserId, UserRegister, UserLoginWithEmail, UserLoginWithName,
    PermissionEdit, UsersGet, EmailVerifySuper, UsersFindByName, PasswordChange)
from query import find_by, _guard_db, get_header_token

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

RESTRICTED_USER_NAMES = ["admin", "root", "guest", "null", "nil", "undefined", "postgres", "localhost"]


@router.post("/register/")
async def register_user(user_register: UserRegister,
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
        # User exists.
        raise HTTPException(status_code=400, detail="Email already registered.")

    if user_register.name in RESTRICTED_USER_NAMES:
        # An easter egg.
        raise HTTPException(status_code=400, detail="You're smart, but this user name is invalid.")

    # Encrypt user password
    hashed_password = pwd_context.hash(user_register.password)

    # Create new user
    new_user = User(email=user_register.email, password_hash=hashed_password, name=user_register.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate JWT token for email confirmation
    token = generate_jwt(new_user.id)

    return {
        "msg": "OK",
        "user_id": str(new_user.id),
        "token": token,
        "detail": "User registered successfully. Please check your mailbox."
    }


@router.get("/verify_email/")
async def verify_email(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    """
    New user email verification.
    :param user_id: UUID of the new user.
    :param token: JWT token of the user.
    :param db: Database object.
    :return: Verification result.
    """
    validate_user(user_id=user_id, token=token)

    db_user = find_by(orm=User,
                      attr="id",
                      val=user_id,
                      fail_detail=f"User with id {user_id} is not found.",
                      db=db)

    if db_user.is_verified:
        raise HTTPException(status_code=400, detail=f"Email already verified.")

    db_user.is_verified = True
    db.commit()

    return {"msg": "Email verified successfully."}


@router.post("/verify_email_super/")
async def verify_email_super(
        email_verify_super: EmailVerifySuper,
        token: str = Depends(get_header_token),
        db=Depends(get_db)):
    """
    Manual email verification by superuser.
    :param email_verify_super: Email verification data.
    :param token: Authorization JWT token.
    :param db: Database session.
    :return:
    """
    _guard_db(auth=email_verify_super, token=token, permission=GRANT_PERMISSION, db=db)

    db_user = find_by(orm=User,
                      attr="id",
                      val=email_verify_super.verify_user_id,
                      fail_detail=f"Can't verify user with id {email_verify_super}: "
                                  f"User not found.",
                      db=db)

    db_user.verify_email()
    db.commit()

    return {"msg": "Email verified by super user successfully."}


@router.post("/login/")
async def login_user(
        user_login: Union[UserLoginWithEmail, UserLoginWithName],
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
    if (not db_user or not isinstance(db_user, User) or
            not pwd_context.verify(user_login.password, db_user.password_hash)):
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
async def delete_user(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    """
    Delete existing user.
    :param user_id: UUID of the user.
    :param token: JWT token of the user.
    :param db: Database object.
    :return: Deletion result.
    """
    validate_user(user_id, token)

    db_user = find_by(orm=User,
                      attr="id",
                      val=user_id,
                      fail_detail=f"User with id {user_id} is not found.",
                      db=db)

    db.delete(db_user)
    db.commit()

    return {"msg": "User deleted successfully.", "user_id": str(user_id)}


@router.post("/change_password/")
async def change_password(
        password_change: PasswordChange,
        token: str = Depends(get_header_token),
        db: Session = Depends(get_db)):
    """
    User change password.
    :param password_change: User password change schema.
    :param token: Authorization JWT token.
    :param db: Database object.
    """
    validate_user(password_change.user_id, token)

    db_user = find_by(orm=User,
                      attr="id",
                      val=password_change.user_id,
                      db=db)

    hashed_password = pwd_context.hash(password_change.new_password)

    db_user.change_password(new_password_hash=hashed_password)
    db_user.verify_email(verify=False)
    db.commit()
    db.refresh(db_user)

    return {
        "msg": f"Successfully updated password for user {password_change.user_id}."
    }


@router.post("/get_user/")
async def get_user(
        with_user_id: WithUserId,
        token: str = Depends(get_header_token),
        db: Session = Depends(get_db)):
    """
    Get information of a specific user.
    :param with_user_id: User authentication schema.
    :param token: Authorization JWT token.
    :param db: Database object.
    :return: The information of the user.
    """
    validate_user(with_user_id.user_id, token)

    db_user = find_by(orm=User,
                      attr="id",
                      val=with_user_id.user_id,
                      db=db)

    return {
        "user_id": str(db_user.id),
        "created_at": str(db_user.created_at),
        "email": db_user.email,
        "name": db_user.name,
        "permissions": db_user.permissions
    }


@router.post("/get_users/")
async def get_users(
        users_get: UsersGet,
        token: str = Depends(get_header_token),
        db: Session = Depends(get_db)):
    """
    Superuser function: Get users from a given range.
    :param users_get: Users get data.
    :param token: Authorization JWT token.
    :param db: Database session.
    :return:
    """

    _guard_db(auth=users_get, token=token, permission=GRANT_PERMISSION, db=db)

    _limit = users_get.range_to - users_get.range_from + 1

    if _limit < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid range.")

    _offset = users_get.range_from

    total_num = db.query(User).count()

    db_users = db.query(User).order_by(desc(
        cast("ColumnElement[_T]", User.created_at)
    )).offset(_offset).limit(_limit).all()

    return {
        "num_total": total_num,
        "num_this_page": len(db_users),
        "users": [{
                    "user_id": str(db_user.id),
                    "created_at": str(db_user.created_at),
                    "email": db_user.email,
                    "name": db_user.name,
                    "permissions": db_user.permissions,
                    "password_hash": str(db_user.password_hash),
                    "is_verified": db_user.is_verified
                  } for db_user in db_users]
    }


@router.post("/find_users/")
async def find_users(
        users_find: UsersFindByName,
        token: str = Depends(get_header_token),
        db: Session = Depends(get_db)):
    """
    Get a list of users with a search query. If the query is not given,
    all users are returned, i.e., matches the empty query.
    :param users_find: Users find data.
    :param token: Authorization JWT token.
    :param db: Database object.
    :return: A list of users that matches the query.
    """

    _guard_db(auth=users_find, token=token, permission=READ, db=db)

    db_users = db.query(User).filter(User.name.ilike(f"%{users_find.query}%")).all()

    return {
        "users": [{
                    "user_id": str(db_user.id),
                    "created_at": str(db_user.created_at),
                    "email": db_user.email,
                    "name": db_user.name,
                    "permissions": db_user.permissions,
                    "password_hash": str(db_user.password_hash),
                    "is_verified": db_user.is_verified
                  } for db_user in db_users]
    }


@router.post("/edit_permission/")
async def edit_permission(
        permission_edit: PermissionEdit,
        token: str = Depends(get_header_token),
        db: Session = Depends(get_db)):
    """
    Superuser function: To grant or revoke other user's permission of access, one at a time.
    :param permission_edit: Permission grant data.
    :param token: Authorization JWT token.
    :param db: Database object.
    :return: Result of permission granting.
    """

    '''
    Operator
    '''
    # validate_user(permission_edit.operator_user_id, permission_edit.token)
    _guard_db(auth=permission_edit, token=token, permission=GRANT_PERMISSION, db=db)

    '''
    Permission Applier
    '''
    db_requester_user = find_by(orm=User,
                                attr="id",
                                val=permission_edit.requester_user_id,
                                fail_detail=f"Requestor {permission_edit.requester_user_id} not found.",
                                db=db)

    if permission_edit.grant:
        db_requester_user.grant_permission(permission_edit.permission)
    else:
        db_requester_user.revoke_permission(permission_edit.permission)

    db.commit()

    return {
        "msg": "Grant permission successful.",
        "user_id": str(permission_edit.requester_user_id),
        "permission": permission_edit.permission,
    }
