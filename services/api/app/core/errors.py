from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, *, retryable: bool = False):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(code)


def error_response(request: Request, error: APIError) -> JSONResponse:
    headers = {
        "Cache-Control": "no-store",
        "X-Request-ID": getattr(request.state, "request_id", "unavailable"),
    }
    if error.status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if error.status == 429:
        headers["Retry-After"] = "60"
    return JSONResponse(
        status_code=error.status,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "retryable": error.retryable,
                "request_id": getattr(request.state, "request_id", "unavailable"),
            }
        },
        headers=headers,
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PyMongoError)
    async def database_unavailable(request: Request, exc: PyMongoError):
        return error_response(
            request,
            APIError(
                503,
                "DATABASE_UNAVAILABLE",
                "Database operation could not complete",
                retryable=True,
            ),
        )

    @app.exception_handler(APIError)
    async def domain_error(request: Request, exc: APIError):
        return error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Pydantic errors can include raw inputs, secrets, and private answer content.
        return error_response(request, APIError(422, "INVALID_INPUT", "Invalid request data"))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(request, APIError(exc.status_code, "HTTP_ERROR", "Request rejected"))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        # Never return database strings, adapter errors, or tracebacks to the client.
        return error_response(
            request, APIError(500, "INTERNAL_ERROR", "Request failed", retryable=True)
        )
