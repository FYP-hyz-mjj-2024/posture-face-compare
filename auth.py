import os
import jwt
import secrets
from dotenv import load_dotenv
import datetime
import uuid
from fastapi import HTTPException, status, Header

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("Missing critical environment variable: "
                     "Environment variable SECRET_KEY is not configured.")

credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                     detail="Could not validate authorization credentials.",
                                     headers={"WWW-Authenticate": "Bearer"}, )


def generate_secret_key(byte_num: int = 32):
    secret_key = secrets.token_urlsafe(byte_num)
    return secret_key


def generate_jwt(user_id: uuid.UUID):
    """
    Generate JWT token.
    :param user_id: User ID.
    :return: JWT token.
    """
    payload = {
        "user_id": str(user_id),
        "exp": datetime.datetime.now() + datetime.timedelta(days=30)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_jwt(token):
    """
    Verify JWT token.
    :param token: JWT token.
    :return: If JWT is valid, return payload. Otherwise, return None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def validate_user(
        user_id: uuid.UUID,
        token: str = Header(..., alias="Authorization")):
    """
    Validate a given user id with a jwt token. Prevents: Expired token, invalid token, unmatched token.
    :param user_id: User ID.
    :param token: JWT token.
    :return:
    """

    if not token:
        raise credential_exception

    token = token.split(" ")[1] if " " in token else token

    # If the token expires or is invalid, exception will be raised here.
    payload = verify_jwt(token)
    if payload is None:
        raise credential_exception

    token_user_id = payload.get("user_id")
    if token_user_id is None:
        raise credential_exception

    if str(user_id) != token_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Authorization token can't be verified specifically for this user.")

    return True
