import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from dotenv import load_dotenv

from database import get_db
import models

load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env (for local dev) or set it "
            f"as a real environment variable on your host before starting the API."
        )
    return value


SECRET_KEY = _require_env("MEDIDIAG_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Admin sign-up PIN, checked server-side (it was previously checked in the
# browser, which meant it was trivially visible in the frontend bundle).
ADMIN_SIGNUP_PIN = _require_env("MEDIDIAG_ADMIN_PIN")

import bcrypt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    if not user.active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.account_type != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return current_user
