# FastAPI server essentials
from typing import Union, cast, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import uuid

# PostgreSQL database connection
from sqlalchemy import desc
from sqlalchemy.orm import Session

# Information Security
from passlib.context import CryptContext

# Locals
from auth import generate_jwt, validate_user, send_verification_email
from database import get_db
from CRUD.user.models import User, GRANT_PERMISSION
from CRUD.user.schemas import UserAuth, UserRegister, UserLoginWithEmail, UserLoginWithName, PermissionGrant, UsersGet, \
    EmailVerifySuper
from query import find_by, _guard_db

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PERMITTED_USER_NAMES = ["admin", "root", "guest", "null", "nil", "undefined"]


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
        # User exists, resend email.
        token = generate_jwt(db_user.id)
        send_verification_email(email_to=db_user.email, user_id=db_user.id, token=token)
        raise HTTPException(status_code=400, detail="Email already registered. Re-sending email.")

    if user_register.name in PERMITTED_USER_NAMES:
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

    # Send verification email
    send_verification_email(email_to=new_user.email, user_id=new_user.id, token=token)

    return {
        "msg": "OK",
        "user_id": str(new_user.id),
        "token": token,
        "detail": "User registered successfully. Please check your mailbox."
    }


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
def verify_email_super(email_verify_super: EmailVerifySuper, db=Depends(get_db)):
    """
    Manual email verification by superuser.
    :param email_verify_super: Email verification data.
    :param db: Database session.
    :return:
    """
    _guard_db(auth=email_verify_super, permission=GRANT_PERMISSION, db=db)
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
def delete_user(user_id: uuid.UUID, token: str, db: Session = Depends(get_db)):
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


@router.post("/get_user/")
def get_user(user_auth: UserAuth, db: Session = Depends(get_db)):
    """
    Get information of a specific user.
    :param user_auth: User authentication schema.
    :param db: Database object.
    :return: The information of the user.
    """
    validate_user(user_auth.user_id, user_auth.token)

    db_user = find_by(orm=User,
                      attr="id",
                      val=user_auth.user_id,
                      fail_detail=f"User with id {user_auth.user_id} is not found.",
                      db=db)

    return {
        "user_id": str(db_user.id),
        "created_at": str(db_user.created_at),
        "email": db_user.email,
        "name": db_user.name,
        "permissions": db_user.permissions
    }


@router.post("/get_users/")
def get_users(users_get: UsersGet, db: Session = Depends(get_db)):
    """
    Get users from a given range.
    :param users_get: Users get data.
    :param db: Database session.
    :return:
    """

    _guard_db(auth=users_get, permission=GRANT_PERMISSION, db=db)

    _limit = users_get.range_to - users_get.range_from + 1

    if _limit < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid range.")

    _offset = users_get.range_from

    total_num = db.query(User).count()

    db_users = db.query(User).order_by(desc(User.created_at)).offset(_offset).limit(_limit).all()

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
def find_users(query: str = "", db: Session = Depends(get_db)):
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
def grant_permission(permission_grant: PermissionGrant,
                     db: Session = Depends(get_db)):
    """
    The ability of a superuser to grant other user access.
    :param permission_grant: Permission grant data.
    :param db: Database object.
    :return: Result of permission granting.
    """

    '''
    Operator
    '''
    validate_user(permission_grant.operator_user_id, permission_grant.token)

    db_operator_user = find_by(orm=User,
                               attr="id",
                               val=permission_grant.operator_user_id,
                               fail_detail=f"Operator {permission_grant.operator_user_id} not found.",
                               db=db)

    # Operator has no permission to grant other's access.
    if not db_operator_user.check_permission(permission=GRANT_PERMISSION):
        raise HTTPException(status_code=403, detail=f"Operator {permission_grant.requester_user_id} "
                                                    f"is not allowed to grant permission.")

    '''
    Permission Applier
    '''
    db_requester_user = find_by(orm=User,
                                attr="id",
                                val=permission_grant.requester_user_id,
                                fail_detail=f"Requestor {permission_grant.requester_user_id} not found.",
                                db=db)

    db_requester_user.grant_permission(permission_grant.permission)
    db.commit()

    return {
        "msg": "Grant permission successful.",
        "user_id": str(permission_grant.requester_user_id),
        "permission": permission_grant.permission,
    }



