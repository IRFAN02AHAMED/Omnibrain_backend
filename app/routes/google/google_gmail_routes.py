# app/routes/google/google_gmail_routes.py
# Purpose: Gmail API routes for listing, reading, and searching emails.

from fastapi import APIRouter, Query

from app.services.google.google_gmail_service import (
    list_gmail_messages,
    read_gmail_message,
    search_gmail_messages,
)

# TODO: Replace `user_id` query parameter with current logged-in user from JWT dependency later.

router = APIRouter(prefix="/google/gmail", tags=["Google Gmail"])


@router.get("/messages")
async def gmail_messages(
    user_id: int = Query(..., description="User ID"),
    max_results: int = Query(10, description="Maximum number of messages to return"),
):
    """
    List recent Gmail messages.

    Returns message IDs and thread IDs (stubs only, not full content).
    Use GET /messages/{message_id} to read full message content.

    Example:
        GET /google/gmail/messages?user_id=1&max_results=10
    """
    return list_gmail_messages(user_id=user_id, max_results=max_results)


@router.get("/messages/{message_id}")
async def gmail_read_message(
    message_id: str,
    user_id: int = Query(..., description="User ID"),
):
    """
    Read a specific Gmail message with full content.

    Returns from, to, subject, date, snippet, body, and label_ids.

    Example:
        GET /google/gmail/messages/MESSAGE_ID?user_id=1
    """
    return read_gmail_message(user_id=user_id, message_id=message_id)


@router.get("/search")
async def gmail_search(
    user_id: int = Query(..., description="User ID"),
    query: str = Query(..., description="Gmail search query (same syntax as Gmail web UI)"),
    max_results: int = Query(10, description="Maximum number of results to return"),
):
    """
    Search Gmail messages using Gmail search syntax.

    Examples: "from:someone@gmail.com", "subject:meeting", "has:attachment"

    Example:
        GET /google/gmail/search?user_id=1&query=from:someone@gmail.com&max_results=10
    """
    return search_gmail_messages(user_id=user_id, query=query, max_results=max_results)
