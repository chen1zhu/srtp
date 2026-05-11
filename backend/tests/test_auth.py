import os
import pathlib
import sys
import tempfile

from fastapi.testclient import TestClient

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DIR = pathlib.Path(tempfile.gettempdir()) / 'srtp_auth_tests'
TEST_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = TEST_DIR / 'users.sqlite3'
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ['USER_DB_PATH'] = str(DB_PATH)
os.environ['ALLOW_SELF_REGISTER'] = 'true'
os.environ['ADMIN_USERNAME'] = 'admin'
os.environ['ADMIN_PASSWORD'] = 'adminpass'
os.environ['ADMIN_EMAIL'] = 'admin@example.com'
os.environ['ADMIN_FULL_NAME'] = '管理员'

from backend.main import app


def make_client() -> TestClient:
    return TestClient(app)


def test_login_and_me_and_logout():
    client = make_client()

    resp = client.post('/auth/login', json={'identifier': 'admin', 'password': 'adminpass'})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('ok') is True
    assert data['user']['email'] == 'admin@example.com'

    resp2 = client.get('/auth/me')
    assert resp2.status_code == 200
    assert resp2.json().get('user', {}).get('username') == 'admin'

    resp3 = client.post('/auth/logout')
    assert resp3.status_code == 200
    assert resp3.json().get('ok') is True


def test_register_new_user_then_profile_actions():
    client = make_client()
    username = 'new_user'
    email = 'new_user@example.com'
    resp = client.post(
        '/auth/register',
        json={'username': username, 'email': email, 'password': 'secret1234', 'full_name': '新用户'},
    )
    assert resp.status_code == 200
    assert resp.json().get('ok') is True
    assert resp.json()['user']['email'] == email

    avatar_resp = client.post(
        '/auth/me/avatar',
        files={'file': ('avatar.png', b'\x89PNG\r\n\x1a\n' + b'0' * 32, 'image/png')},
    )
    assert avatar_resp.status_code == 200
    assert avatar_resp.json()['user']['avatar_url'].startswith('/uploads/avatars/')

    password_resp = client.post(
        '/auth/me/password',
        json={'current_password': 'secret1234', 'new_password': 'newsecret1234'},
    )
    assert password_resp.status_code == 200

    client.post('/auth/logout')
    relogin_resp = client.post('/auth/login', json={'identifier': username, 'password': 'newsecret1234'})
    assert relogin_resp.status_code == 200


def test_register_rejects_duplicate_username_and_invalid_email():
    client = make_client()
    duplicate_resp = client.post(
        '/auth/register',
        json={'username': 'admin', 'email': 'another@example.com', 'password': 'secret1234', 'full_name': '重复'},
    )
    assert duplicate_resp.status_code == 409

    invalid_email_resp = client.post(
        '/auth/register',
        json={'username': 'bad_email_user', 'email': 'not-an-email', 'password': 'secret1234', 'full_name': '错误邮箱'},
    )
    assert invalid_email_resp.status_code == 400


def test_register_cors_allows_local_frontend_origin():
    client = make_client()
    resp = client.options(
        '/auth/register',
        headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        },
    )
    assert resp.status_code in (200, 204)
    assert resp.headers.get('access-control-allow-origin') == 'http://localhost:5173'
