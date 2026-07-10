# app/ai/tools/google_tools.py
# Purpose: AI tool wrappers around Google connector services.
# These functions call existing service functions — they do NOT call Google APIs directly.
# They will later become LangGraph tools/nodes for AI-powered Google workflows.
# pip install google-api-python-client google-auth google-auth-oauthlib python-dotenv langgraph langchain-core

from app.services.google.google_drive_service import (
    list_drive_files,
    search_drive_files,
)
from app.services.google.google_docs_service import (
    list_google_docs,
    read_google_doc,
)
from app.services.google.google_sheets_service import (
    list_google_sheets,
    read_sheet_values,
)
from app.services.google.google_gmail_service import (
    list_gmail_messages,
    read_gmail_message,
)

# ─────────────────────────────────────────────────────────────────────────────
# Try to import @tool decorator from langchain_core.
# If not available, use plain functions with a TODO comment.
# ─────────────────────────────────────────────────────────────────────────────

try:
    from langchain_core.tools import tool

    @tool
    def tool_list_drive_files(user_id: int, page_size: int = 10) -> dict:
        """List recent files from a user's Google Drive."""
        return list_drive_files(user_id=user_id, page_size=page_size)

    @tool
    def tool_search_drive_files(user_id: int, query: str, page_size: int = 10) -> dict:
        """Search Google Drive files by name."""
        return search_drive_files(user_id=user_id, query=query, page_size=page_size)

    @tool
    def tool_list_google_docs(user_id: int, page_size: int = 10) -> dict:
        """List Google Docs from a user's Drive."""
        return list_google_docs(user_id=user_id, page_size=page_size)

    @tool
    def tool_read_google_doc(user_id: int, document_id: str) -> dict:
        """Read the content of a specific Google Doc."""
        return read_google_doc(user_id=user_id, document_id=document_id)

    @tool
    def tool_list_google_sheets(user_id: int, page_size: int = 10) -> dict:
        """List Google Sheets from a user's Drive."""
        return list_google_sheets(user_id=user_id, page_size=page_size)

    @tool
    def tool_read_sheet_values(
        user_id: int, spreadsheet_id: str, range_name: str = "Sheet1!A1:Z100"
    ) -> dict:
        """Read values from a specific Google Sheet range."""
        return read_sheet_values(
            user_id=user_id, spreadsheet_id=spreadsheet_id, range_name=range_name
        )

    @tool
    def tool_list_gmail_messages(user_id: int, max_results: int = 10, query: str = "") -> dict:
        """List recent Gmail messages for a user."""
        return list_gmail_messages(user_id=user_id, max_results=max_results, query=query)

    @tool
    def tool_read_gmail_message(user_id: int, message_id: str) -> dict:
        """Read a specific Gmail message with full content."""
        return read_gmail_message(user_id=user_id, message_id=message_id)

except ImportError:
    # TODO: Install langchain-core and wrap these functions with @tool later.
    # For now, plain Python functions are used.

    def tool_list_drive_files(user_id: int, page_size: int = 10) -> dict:
        """List recent files from a user's Google Drive."""
        return list_drive_files(user_id=user_id, page_size=page_size)

    def tool_search_drive_files(user_id: int, query: str, page_size: int = 10) -> dict:
        """Search Google Drive files by name."""
        return search_drive_files(user_id=user_id, query=query, page_size=page_size)

    def tool_list_google_docs(user_id: int, page_size: int = 10) -> dict:
        """List Google Docs from a user's Drive."""
        return list_google_docs(user_id=user_id, page_size=page_size)

    def tool_read_google_doc(user_id: int, document_id: str) -> dict:
        """Read the content of a specific Google Doc."""
        return read_google_doc(user_id=user_id, document_id=document_id)

    def tool_list_google_sheets(user_id: int, page_size: int = 10) -> dict:
        """List Google Sheets from a user's Drive."""
        return list_google_sheets(user_id=user_id, page_size=page_size)

    def tool_read_sheet_values(
        user_id: int, spreadsheet_id: str, range_name: str = "Sheet1!A1:Z100"
    ) -> dict:
        """Read values from a specific Google Sheet range."""
        return read_sheet_values(
            user_id=user_id, spreadsheet_id=spreadsheet_id, range_name=range_name
        )

    def tool_list_gmail_messages(user_id: int, max_results: int = 10, query: str = "") -> dict:
        """List recent Gmail messages for a user."""
        return list_gmail_messages(user_id=user_id, max_results=max_results, query=query)

    def tool_read_gmail_message(user_id: int, message_id: str) -> dict:
        """Read a specific Gmail message with full content."""
        return read_gmail_message(user_id=user_id, message_id=message_id)
