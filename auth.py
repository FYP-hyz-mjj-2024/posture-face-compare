import os
import jwt
import secrets
from dotenv import load_dotenv
import datetime
from fastapi import HTTPException, status

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("Missing critical environment variable: "
                     "Environment variable SECRET_KEY is not configured.")


def generate_secret_key(byte_num: int = 32):
    secret_key = secrets.token_urlsafe(byte_num)
    return secret_key


def generate_jwt(user_id):
    """
    Generate JWT token.
    :param user_id: User ID.
    :return: JWT token.
    """
    payload = {
        "user_id": user_id,
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
