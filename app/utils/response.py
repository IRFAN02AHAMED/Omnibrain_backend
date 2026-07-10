"""
response.py — Unified API Response Builder
==========================================
Every API endpoint must return the same JSON envelope:

    {
        "success": true,
        "status_code": 200,
        "message": "Operation completed.",
        "data": { ... },
        "timestamp": "2025-01-01T12:00:00Z"
    }

HOW TO USE:
    from app.utils.response import ResponseBuilder

    # Success
    return ResponseBuilder.success(data=user_dict, message="User created.")

    # Error (raise as HTTPException or return directly)
    return ResponseBuilder.error(message="Not found.", status_code=404)
"""

from datetime import datetime, timezone
from typing import Any, Optional
from fastapi.responses import JSONResponse


class ResponseBuilder:
    """
    Static factory class that creates standardised API response dictionaries.
    No instances needed — call the class methods directly.
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Request completed successfully.",
        status_code: int = 200,
    ) -> JSONResponse:
        """
        Creates a successful JSON response.

        Args:
            data:        The payload to return (dict, list, or None).
            message:     Human-readable success message.
            status_code: HTTP status code (default 200).

        Returns:
            FastAPI JSONResponse with the standard envelope.

        Example:
            return ResponseBuilder.success(data={"id": "abc"}, message="Created.", status_code=201)
        """
        body = {
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(content=body, status_code=status_code)

    @staticmethod
    def error(
        message: str = "An unexpected error occurred.",
        status_code: int = 500,
        data: Any = None,
    ) -> JSONResponse:
        """
        Creates an error JSON response.

        Args:
            message:     Human-readable error description.
            status_code: HTTP error status code.
            data:        Optional extra context (e.g. validation error details).

        Returns:
            FastAPI JSONResponse with success=False.

        Example:
            return ResponseBuilder.error(message="Document not found.", status_code=404)
        """
        body = {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(content=body, status_code=status_code)

    @staticmethod
    def paginated(
        items: list,
        total: int,
        page: int,
        page_size: int,
        message: str = "Data fetched successfully.",
    ) -> JSONResponse:
        """
        Creates a paginated success response.

        Args:
            items:     List of records for the current page.
            total:     Total number of matching records.
            page:      Current page number (1-indexed).
            page_size: Number of records per page.
            message:   Human-readable message.

        Returns:
            JSONResponse with pagination metadata in data.

        Example:
            return ResponseBuilder.paginated(items=docs, total=100, page=1, page_size=10)
        """
        total_pages = max(1, (total + page_size - 1) // page_size)
        body = {
            "success": True,
            "status_code": 200,
            "message": message,
            "data": {
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(content=body, status_code=200)
