import hashlib
import hmac
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET
from .user_store import AVATAR_DIR, create_user, get_user_by_identifier, get_user_by_username, is_valid_email, update_user_avatar, update_user_password

router = APIRouter()

# 简单的演示用用户存储（生产应替换为数据库）
# 口径：管理员与普通用户使用同一套密码存储/校验逻辑（哈希 + 常量时间比较）。
PASSWORD_SALT = os.environ.get("PASSWORD_SALT", "srtp-dev-salt")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.local")
ADMIN_FULL_NAME = os.environ.get("ADMIN_FULL_NAME", "管理员")
AUTH_COOKIE_SECURE = os.environ.get("AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
ALLOW_SELF_REGISTER = os.environ.get("ALLOW_SELF_REGISTER", "true").lower() in {"1", "true", "yes"}
MIN_PASSWORD_LENGTH = int(os.environ.get("MIN_PASSWORD_LENGTH", "8"))
ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def hash_password(raw_password: str) -> str:
    return hashlib.sha256(f"{PASSWORD_SALT}:{raw_password}".encode("utf-8")).hexdigest()


def verify_password(raw_password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(raw_password), password_hash)


class LoginRequest(BaseModel):
    identifier: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


def _bootstrap_admin_user() -> None:
    existing = get_user_by_username(ADMIN_USERNAME)
    if existing:
        return
    create_user(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        full_name=ADMIN_FULL_NAME,
        role="admin",
    )


_bootstrap_admin_user()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def get_current_user_from_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        return get_user_by_username(username)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def _issue_login_cookie(response: Response, username: str):
    access_token = create_access_token({"sub": username})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=AUTH_COOKIE_SECURE,
    )


def _serialize_user(user: dict) -> dict:
    return {
        "username": user["username"],
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role", "user"),
        "avatar_url": user.get("avatar_url"),
    }


def _require_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="未认证")
    user = get_current_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="未认证")
    return user


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    user = get_user_by_identifier(req.identifier)
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # HttpOnly cookie，前端请求需带上 credentials: 'include'
    _issue_login_cookie(response, user["username"])
    return {"ok": True, "user": _serialize_user(user)}


@router.post("/register")
async def register(req: RegisterRequest, response: Response):
    if not ALLOW_SELF_REGISTER:
        raise HTTPException(status_code=403, detail="当前环境不允许自助注册")

    username = req.username.strip()
    email = req.email.strip()
    full_name = req.full_name.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if not full_name:
        raise HTTPException(status_code=400, detail="姓名不能为空")
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if len(req.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"密码至少需要 {MIN_PASSWORD_LENGTH} 位")

    try:
        user = create_user(
            username=username,
            email=email,
            password_hash=hash_password(req.password),
            full_name=full_name,
            role="user",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _issue_login_cookie(response, username)
    return {
        "ok": True,
        "user": _serialize_user(user),
    }


@router.get("/me")
async def me(request: Request):
    user = _require_current_user(request)
    return {"user": _serialize_user(user)}


@router.post("/me/password")
async def change_password(req: PasswordChangeRequest, request: Request):
    user = _require_current_user(request)
    if not verify_password(req.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="当前密码错误")
    if len(req.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"密码至少需要 {MIN_PASSWORD_LENGTH} 位")
    update_user_password(user["username"], hash_password(req.new_password))
    return {"ok": True}


@router.post("/me/avatar")
async def update_avatar(request: Request, file: UploadFile = File(...)):
    user = _require_current_user(request)
    content_type = (file.content_type or "").lower()
    suffix = ALLOWED_AVATAR_CONTENT_TYPES.get(content_type)
    if suffix is None:
      raise HTTPException(status_code=400, detail="仅支持 png、jpeg、webp、gif 图片")

    avatar_name = f"{user['username']}_{uuid.uuid4().hex}{suffix}"
    avatar_path = AVATAR_DIR / avatar_name
    with avatar_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)

    avatar_url = f"/uploads/avatars/{avatar_name}"
    update_user_avatar(user["username"], avatar_url)
    updated_user = get_user_by_username(user["username"])
    if not updated_user:
        raise HTTPException(status_code=500, detail="头像更新失败")
    return {"ok": True, "user": _serialize_user(updated_user)}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}
