"""
exception_handler.py — Global Error Handler Middleware
=======================================================
Catches all unhandled exceptions and returns them in the
standard API response envelope instead of raw FastAPI errors.

This ensures EVERY response (success or error) looks like:
  {
    "success": false,
    "status_code": 422,
    "message": "Validation error details...",
    "data": null,
    "timestamp": "..."
  }

HOW IT'S REGISTERED:
    In main.py:
        from app.middleware.exception_handler import register_exception_handlers
        register_exception_handlers(app)
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from app.core.logger import logger


def _error_envelope(status_code: int, message: str, data=None) -> dict:
    """
    Builds the standard error response body.

    Args:
        status_code: HTTP status code.
        message:     Human-readable error description.
        data:        Optional extra context (e.g. validation details).

    Returns:
        Dict matching the standard API response shape.
    """
    return {
        "success":     False,
        "status_code": status_code,
        "message":     message,
        "data":        data,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
    }


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers all global exception handlers on the FastAPI app.

    Call this once during application startup in main.py.

    Handles:
      - HTTPException          — FastAPI raises these for 400/401/403/404/409 etc.
      - RequestValidationError — Pydantic validation failures (422)
      - Exception              — Catch-all for unexpected server errors (500)

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Handles intentionally raised HTTPExceptions.
        These come from services and security utilities.
        Example: raise HTTPException(status_code=404, detail="Not found")
        """
        logger.warning(
            f"HTTPException [{exc.status_code}] on {request.method} {request.url.path}: {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope(
                status_code=exc.status_code,
                message=str(exc.detail),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handles Pydantic schema validation failures.
        These happen when the client sends wrong types or missing required fields.

        Example error: "field 'email' must be a valid email address"

        Returns 422 with a list of field-level validation errors.
        """
        errors = exc.errors()
        # Build a readable summary: "body.email: value is not a valid email address"
        messages = []
        for err in errors:
            loc   = " → ".join(str(l) for l in err.get("loc", []))
            msg   = err.get("msg", "Invalid value")
            messages.append(f"{loc}: {msg}")

        readable_message = " | ".join(messages)

        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {readable_message}"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_envelope(
                status_code=422,
                message=f"Request validation failed: {readable_message}",
                data=errors,
            ),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """
        Catch-all handler for unexpected server errors.
        Logs the full traceback but returns a safe message to the client
        (never expose raw Python exceptions to users in production).
        """
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                status_code=500,
                message="An unexpected server error occurred. Please try again later.",
            ),
        )
