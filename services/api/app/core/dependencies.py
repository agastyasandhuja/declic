import inspect
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from app.core import collections as tables
from app.core.errors import APIError
from app.core.identity import Principal

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(401, "AUTH_REQUIRED", "An app access token is required")
    if len(credentials.credentials) > 16384:
        raise APIError(401, "INVALID_TOKEN", "Invalid or expired access token")
    verify = request.app.state.identity.verify_access_token
    if inspect.iscoroutinefunction(verify):
        user = await verify(credentials.credentials)
    else:
        user = await run_in_threadpool(verify, credentials.credentials)
        if inspect.isawaitable(user):
            user = await user
    if not isinstance(user, Principal) or not user.user_id or len(user.user_id) > 128:
        raise APIError(503, "AUTH_UNAVAILABLE", "Identity verification failed", retryable=True)
    database = request.app.state.database
    minute = int(request.app.state.clock().timestamp() // 60)

    def operation(conn):
        row = conn.find_one(tables.users, {"user_id": user.user_id})
        count = row["rate_count"] if row["rate_window"] == minute else 0
        if count >= database.settings.rate_limit_per_minute:
            raise APIError(429, "RATE_LIMITED", "Too many requests", retryable=True)
        conn.update(
            tables.users,
            {"user_id": user.user_id},
            {"rate_count": count + 1, "rate_window": minute},
        )

    await run_in_threadpool(database.run, user.user_id, operation)
    return user


CurrentUser = Annotated[Principal, Depends(get_current_user)]
