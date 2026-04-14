from .db import insert_credentials, fetch_credentials_if_exist
from jose import jwt, ExpiredSignatureError, JWTError
import secrets
import datetime
from fastapi import HTTPException
from starlette.requests import Request
from flask import session

SECRET_KEY = secrets.token_hex(20)
ALGORITHM = "HS256"
TOKEN_LIFETIME_MINUTES = 60 * 24 * 7  # 1 week


def add_credentials(email: str, password: str) -> None:
    insert_credentials([{"email": email, "password": password}])


def check_credentials(email: str) -> dict | None:
    return fetch_credentials_if_exist(email)


def create_jwt(email: str) -> str:
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=TOKEN_LIFETIME_MINUTES
    )
    payload = {
        "sub": email,
        "iat": datetime.datetime.now(datetime.UTC),
        "exp": expire,
    }
    return jwt.encode(payload, key=SECRET_KEY, algorithm=ALGORITHM)


def parse_token_from_starlette(request: Request) -> str:
    bearer = request.headers.get("Authorization", None)
    if bearer is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not bearer.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header malformed")
    return bearer.split(" ")[1]


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token expired") from e
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


def parse_token_from_flask() -> str | None:
    bearer = session.get("Authorization", None)
    if bearer is None:
        return None
    if not bearer.startswith("Bearer "):
        return None
    return bearer.split(" ")[1]