import inspect
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import jwt
from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlmodel import select

from app.models import User
from app.services.postgres import get_session

UnauthorizedException = HTTPException(
    status_code=401,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class LoginManager(OAuth2PasswordBearer):
    def __init__(
        self,
        token_url: str,
        secret: str,
        default_expiry: timedelta = timedelta(minutes=30),
    ) -> None:
        super().__init__(token_url)
        self.default_expiry = default_expiry
        self.algorithm = "HS256"
        self.secret = secret

    async def _load_user(self, user_id: str) -> "Any | None":  # noqa: ANN401
        if self.user_getter_func is None:
            msg = "Missing user_loader callback"
            raise Exception(msg)  # noqa: TRY002

        if inspect.iscoroutinefunction(self.user_getter_func):
            user = await self.user_getter_func(user_id)
        else:
            user = self.user_getter_func(user_id)

        return user

    async def _request_to_token(self, request: Request) -> str:
        token = None

        token = await super().__call__(request)

        if not token:
            logger.warning("Failed to get Bearer token")
            raise UnauthorizedException

        return token

    async def _token_to_payload(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])

        except jwt.PyJWTError as e:
            logger.exception(e)  # noqa: TRY401
            logger.warning("Failed to decode JWT: `%s`", token)
            raise UnauthorizedException from None

    async def _payload_to_user(self, payload: dict[str, Any]) -> User:
        user_id = payload.get("sub")

        if user_id is None:
            logger.warning("Failed to get user id")
            raise UnauthorizedException

        user = await self._load_user(user_id)

        if user is None:
            logger.warning("Failed to get user")
            raise UnauthorizedException

        return user

    def create_access_token(
        self, user_id: str, expiry: "timedelta | None" = None
    ) -> str:
        expiry = expiry or self.default_expiry

        payload = {
            "sub": user_id,
            "exp": (datetime.now(tz=UTC) + expiry),
        }

        token = jwt.encode(payload, key=self.secret, algorithm=self.algorithm)
        logger.warning("Generated token: `%s`", token)

        return token

    async def get_current_user(self, token: str) -> Any:  # noqa: ANN401
        payload = await self._token_to_payload(token)
        return await self._payload_to_user(payload)

    def user_getter(self, func: Callable[[str], Any]) -> Callable[[str], Any]:
        self.user_getter_func = func

        return func

    async def __call__(
        self,
        request: Request,
        security_scopes: SecurityScopes = None,  # type: ignore  # noqa: ARG002
    ) -> Any:  # noqa: ANN401
        logger.warning("Authorization request: %s", request.headers)
        token = await self._request_to_token(request)
        payload = await self._token_to_payload(token)

        return await self._payload_to_user(payload)


SECRET_KEY = os.environ["AUTH_SECRET"]

login_manager = LoginManager(
    token_url="/auth/login",  # noqa: S106
    secret=SECRET_KEY,
    default_expiry=timedelta(days=7),
)


@login_manager.user_getter
def load_user(user_id: str) -> "User | None":
    with next(get_session()) as session:
        return session.exec(select(User).where(User.login == user_id)).first()
