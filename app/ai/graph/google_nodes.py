# app/ai/graph/google_nodes.py
# Purpose: LangGraph node functions for Google actions.
# Each node reads values from state, calls the matching Google tool function,
# and returns an updated state dictionary with the result.
# pip install google-api-python-client google-auth google-auth-oauthlib python-dotenv langgraph langchain-core

from app.ai.tools.google_tools import (
    tool_list_drive_files,
    tool_search_drive_files,
    tool_list_google_docs,
    tool_read_google_doc,
    tool_list_google_sheets,
    tool_read_sheet_values,
    tool_list_gmail_messages,
    tool_read_gmail_message,
)


def list_drive_node(state: dict) -> dict:
    """
    LangGraph node: List files from Google Drive.

    Expected state keys:
        - user_id (int): The application user ID.
        - page_size (int, optional): Number of files. Defaults to 10.

    Returns:
        dict: Updated state with 'result' key containing Drive files.
    """
    user_id = state["user_id"]
    page_size = state.get("page_size", 10)
    result = tool_list_drive_files(user_id=user_id, page_size=page_size)
    return {**state, "result": result}


def search_drive_node(state: dict) -> dict:
    """
    LangGraph node: Search Google Drive files by name.

    Expected state keys:
        - user_id (int): The application user ID.
        - query (str): Search query text.
        - page_size (int, optional): Number of results. Defaults to 10.

    Returns:
        dict: Updated state with 'result' key containing search results.
    """
    user_id = state["user_id"]
    query = state["query"]
    page_size = state.get("page_size", 10)
    result = tool_search_drive_files(user_id=user_id, query=query, page_size=page_size)
    return {**state, "result": result}


def list_docs_node(state: dict) -> dict:
    """
    LangGraph node: List Google Docs from Drive.

    Expected state keys:
        - user_id (int): The application user ID.
        - page_size (int, optional): Number of documents. Defaults to 10.

    Returns:
        dict: Updated state with 'result' key containing document list.
    """
    user_id = state["user_id"]
    page_size = state.get("page_size", 10)
    result = tool_list_google_docs(user_id=user_id, page_size=page_size)
    return {**state, "result": result}


def read_doc_node(state: dict) -> dict:
    """
    LangGraph node: Read a specific Google Doc.

    Expected state keys:
        - user_id (int): The application user ID.
        - document_id (str): The Google Docs document ID.

    Returns:
        dict: Updated state with 'result' key containing document content.
    """
    user_id = state["user_id"]
    document_id = state["document_id"]
    result = tool_read_google_doc(user_id=user_id, document_id=document_id)
    return {**state, "result": result}


def list_sheets_node(state: dict) -> dict:
    """
    LangGraph node: List Google Sheets from Drive.

    Expected state keys:
        - user_id (int): The application user ID.
        - page_size (int, optional): Number of spreadsheets. Defaults to 10.

    Returns:
        dict: Updated state with 'result' key containing spreadsheet list.
    """
    user_id = state["user_id"]
    page_size = state.get("page_size", 10)
    result = tool_list_google_sheets(user_id=user_id, page_size=page_size)
    return {**state, "result": result}


def read_sheet_node(state: dict) -> dict:
    """
    LangGraph node: Read values from a Google Sheet.

    Expected state keys:
        - user_id (int): The application user ID.
        - spreadsheet_id (str): The Google Sheets spreadsheet ID.
        - range_name (str, optional): A1 notation range. Defaults to "Sheet1!A1:Z100".

    Returns:
        dict: Updated state with 'result' key containing sheet values.
    """
    user_id = state["user_id"]
    spreadsheet_id = state["spreadsheet_id"]
    range_name = state.get("range_name", "Sheet1!A1:Z100")
    result = tool_read_sheet_values(
        user_id=user_id, spreadsheet_id=spreadsheet_id, range_name=range_name
    )
    return {**state, "result": result}


def list_gmail_node(state: dict) -> dict:
    """
    LangGraph node: List Gmail messages.

    Expected state keys:
        - user_id (int): The application user ID.
        - max_results (int, optional): Maximum messages. Defaults to 10.
        - query (str, optional): Gmail search query. Defaults to "".

    Returns:
        dict: Updated state with 'result' key containing message list.
    """
    user_id = state["user_id"]
    max_results = state.get("max_results", 10)
    query = state.get("query", "")
    result = tool_list_gmail_messages(user_id=user_id, max_results=max_results, query=query)
    return {**state, "result": result}


def read_gmail_node(state: dict) -> dict:
    """
    LangGraph node: Read a specific Gmail message.

    Expected state keys:
        - user_id (int): The application user ID.
        - message_id (str): The Gmail message ID.

    Returns:
        dict: Updated state with 'result' key containing full message content.
    """
    user_id = state["user_id"]
    message_id = state["message_id"]
    result = tool_read_gmail_message(user_id=user_id, message_id=message_id)
    return {**state, "result": result}
