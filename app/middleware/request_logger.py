"""
request_logger.py — HTTP Request/Response Logging Middleware
=============================================================
Logs every incoming request and outgoing response:
  - Method, path, query params
  - Response status code
  - Time taken in milliseconds

This helps you debug slow endpoints and track API usage.

HOW IT'S REGISTERED:
    In main.py:
        from app.middleware.request_logger import RequestLoggerMiddleware
        app.add_middleware(RequestLoggerMiddleware)
"""


import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logger import logger


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        skip_paths = {"/docs", "/openapi.json", "/redoc", "/favicon.ico"}

        if request.url.path in skip_paths:
            return await call_next(request)

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 2) #to milliseconds
            logger.error(
                f"{request.method} {request.url.path} failed after {elapsed}ms: {exc}"
            )
            raise

        elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({elapsed}ms)"
        )

        return response