from fastapi import APIRouter, HTTPException, status

from app.core.constants import ADMIN_TOKEN_TYPE
from app.core.security import create_token, verify_admin_password
from app.routers.deps import SettingsDep
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.errors import AuthFailedError


router = APIRouter()


def _login_or_raise(*, request: LoginRequest, settings: SettingsDep) -> str:
    if request.username != settings.admin_username:
        raise AuthFailedError()

    expected = settings.admin_password.get_secret_value()
    if not verify_admin_password(expected=expected, provided=request.password):
        raise AuthFailedError()

    return create_token(
        secret=settings.jwt_secret.get_secret_value(),
        token_type=ADMIN_TOKEN_TYPE,
        subject=settings.admin_username,
        expires_in_seconds=settings.admin_token_expires_seconds,
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, settings: SettingsDep) -> LoginResponse:
    try:
        token = _login_or_raise(request=request, settings=settings)
    except AuthFailedError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    return LoginResponse(token=token, expires_in=settings.admin_token_expires_seconds)
