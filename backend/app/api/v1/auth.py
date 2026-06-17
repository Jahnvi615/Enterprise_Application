from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.domain.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.domain.auth.service import AuthService
from app.core.security import get_current_user_id

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register", response_model=TokenResponse)
def register(
    request: RegisterRequest, service: AuthService = Depends(get_auth_service)
):
    return service.register(request)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return service.login(request)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: RefreshRequest, service: AuthService = Depends(get_auth_service)
):
    return service.refresh(request.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user(
    user_id: str = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
):
    user = service.get_user_by_id(user_id)
    if not user:
        from app.exceptions import NotFoundException
        raise NotFoundException("User not found")
    return user
