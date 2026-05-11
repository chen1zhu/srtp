import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
AVATAR_DIR = Path(os.environ.get("AVATAR_DIR", str(BASE_DIR / "uploads" / "avatars")))
DB_PATH = Path(os.environ.get("USER_DB_PATH", str(DATA_DIR / "users.sqlite3")))

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_directories()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                avatar_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _row_to_user(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    return {
        "username": row["username"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "full_name": row["full_name"],
        "role": row["role"],
        "avatar_url": row["avatar_url"],
    }


def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    return _row_to_user(row)


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    normalized_email = normalize_email(email)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()
    return _row_to_user(row)


def get_user_by_identifier(identifier: str) -> Optional[dict[str, Any]]:
    candidate = identifier.strip()
    if not candidate:
        return None
    if "@" in candidate:
        return get_user_by_email(candidate)
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (candidate, normalize_email(candidate)),
        ).fetchone()
    return _row_to_user(row)


def create_user(
    *,
    username: str,
    email: str,
    password_hash: str,
    full_name: str,
    role: str = "user",
) -> dict[str, Any]:
    normalized_username = username.strip()
    normalized_email = normalize_email(email)
    normalized_full_name = full_name.strip()

    with _connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (username, email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (normalized_username, normalized_email, password_hash, normalized_full_name, role),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("用户名或邮箱已存在") from exc

    user = get_user_by_username(normalized_username)
    if user is None:
        raise RuntimeError("用户创建失败")
    return user


def update_user_password(username: str, password_hash: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
            (password_hash, username.strip()),
        )
        conn.commit()


def update_user_avatar(username: str, avatar_url: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET avatar_url = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
            (avatar_url, username.strip()),
        )
        conn.commit()


def ensure_user_exists(**kwargs: Any) -> dict[str, Any]:
    existing = get_user_by_username(kwargs["username"])
    if existing:
      return existing
    return create_user(**kwargs)


init_db()