import os
import jwt
import secrets
from dotenv import load_dotenv
import datetime
import uuid
from fastapi import HTTPException, status, Header

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()
SERVER_DOMAIN = os.getenv('SERVER_DOMAIN')
SECRET_KEY = os.getenv("SECRET_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")

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


def send_verification_email(email_to: str, user_id: str, token: str):
    """
    Send a verification email to the email address of the registered user.
    :param email_to: Destination email address of the registered user.
    :param user_id: UUID of the registered user.
    :param token: JWT token of the registered user.
    :return:
    """
    subject = "Verify email for YFYW backend management"
    verification_url = f"{SERVER_DOMAIN}/user/verify_email/?user_id={user_id}&token={token}"

    html_content = f"""
    <html>
        <main>
            <body>
                <h2>Verify your email.</h2>
                <p>Thanks for registering with us!</p>
                <p>Please click the link below to verify your email address:</p>
                <p><a href="{verification_url}">Verify Email</a></p>
                <p>Please ignore this email if you do not expect this.</p>
            </body>
        </main>
    </html>
    """

    # body = (f"Your user id is: \n{user_id}\n"
    #         f"Your validation token is: \n{token}")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = email_to
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, email_to, msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email:{str(e)}.")


if __name__ == "__main__":
    send_verification_email("hyzumarchive@gmail.com", user_id="UUID_placeholder", token="token_placeholder")

