# app/services/google/google_gmail_service.py
# Purpose: Gmail API logic for listing, reading, and searching emails.

from fastapi import HTTPException

from app.services.google.google_token_store import get_google_account
from app.services.google.google_client_service import get_gmail_client
from app.services.google.google_helper_service import (
    extract_gmail_headers,
    extract_gmail_text,
)


def list_gmail_messages(user_id: int, max_results: int = 10, query: str = "") -> dict:
    """
    List recent Gmail messages for the connected Google account.

    Returns message IDs and thread IDs WITHOUT fetching full message bodies.
    Use read_gmail_message() to get the full content of a specific message.

    Args:
        user_id: The application user ID.
        max_results: Maximum number of messages to return (default: 10).
        query: Optional Gmail search query (e.g., "from:someone@gmail.com").

    Returns:
        dict: Dictionary with 'messages' list (id + threadId), 'count', and 'query'.
    """
    account = get_google_account(user_id)
    service = get_gmail_client(account)

    try:
        params = {
            "userId": "me",
            "maxResults": max_results,
        }
        if query:
            params["q"] = query

        results = service.users().messages().list(**params).execute()
        messages = results.get("messages", [])

        return {
            "messages": messages,
            "count": len(messages),
            "query": query if query else None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Gmail messages: {str(e)}")


def read_gmail_message(user_id: int, message_id: str) -> dict:
    """
    Read a single Gmail message with full content.

    Fetches the full message and extracts:
    - Headers: from, to, subject, date
    - Snippet: short preview text
    - Body: full decoded email body text
    - Label IDs: Gmail labels applied to the message

    Args:
        user_id: The application user ID.
        message_id: The Gmail message ID.

    Returns:
        dict: Dictionary with message details including headers, snippet, and body.
    """
    account = get_google_account(user_id)
    service = get_gmail_client(account)

    try:
        message = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        payload = message.get("payload", {})
        headers = extract_gmail_headers(payload)
        body = extract_gmail_text(payload)
        snippet = message.get("snippet", "")

        return {
            "message_id": message_id,
            "thread_id": message.get("threadId", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "snippet": snippet,
            "body": body,
            "label_ids": message.get("labelIds", []),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read Gmail message: {str(e)}")


def search_gmail_messages(user_id: int, query: str, max_results: int = 10) -> dict:
    """
    Search Gmail messages using a Gmail search query.

    Uses the same search syntax as the Gmail web UI.
    Examples: "from:user@example.com", "subject:meeting", "has:attachment"

    Delegates to list_gmail_messages with the query parameter.

    Args:
        user_id: The application user ID.
        query: Gmail search query string.
        max_results: Maximum number of results to return (default: 10).

    Returns:
        dict: Dictionary with matching message stubs (id + threadId).
    """
    return list_gmail_messages(user_id=user_id, max_results=max_results, query=query)
