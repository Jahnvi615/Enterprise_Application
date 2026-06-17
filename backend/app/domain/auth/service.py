from sqlalchemy.orm import Session
from app.domain.auth.models import User
from app.domain.auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.exceptions import ConflictException, UnauthorizedException
import structlog

logger = structlog.get_logger()


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, request: RegisterRequest) -> TokenResponse:
        existing = self.db.query(User).filter(User.email == request.email).first()
        if existing:
            raise ConflictException("Email already registered")

        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info("user_registered", user_id=user.id, email=user.email)
        return self._create_tokens(user)

    def login(self, request: LoginRequest) -> TokenResponse:
        user = self.db.query(User).filter(User.email == request.email).first()
        if not user or not verify_password(request.password, user.hashed_password):
            raise UnauthorizedException("Invalid credentials")
        if not user.is_active:
            raise UnauthorizedException("Account is disabled")

        logger.info("user_logged_in", user_id=user.id)
        return self._create_tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid refresh token")

        user = self.db.query(User).filter(User.id == payload["sub"]).first()
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        return self._create_tokens(user)

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def _create_tokens(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user.id, {"role": user.role}),
            refresh_token=create_refresh_token(user.id),
        )
