# app/services/google/google_helper_service.py
# Purpose: Convert raw Google API responses into clean readable data.
# Handles Gmail base64 decoding, nested payloads, Docs paragraph extraction,
# and Sheets value formatting.

import base64


def decode_gmail_body(data: str) -> str:
    """
    Decode a base64url-encoded Gmail body string.

    Gmail API returns email body content in base64url encoding.
    This function safely decodes it to a readable UTF-8 string.

    Args:
        data: Base64url-encoded string from Gmail API.

    Returns:
        str: Decoded UTF-8 string. Returns empty string on failure.
    """
    if not data:
        return ""
    try:
        # Gmail uses URL-safe base64 encoding (may need padding)
        decoded_bytes = base64.urlsafe_b64decode(data + "==")
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_gmail_text(payload: dict) -> str:
    """
    Extract readable email body text from a Gmail message payload.

    Gmail payloads can have nested parts (multipart emails).
    This function recursively searches for text/plain first, then text/html.

    Args:
        payload: The 'payload' object from a Gmail message response.

    Returns:
        str: Extracted email body text.
    """
    # If the payload directly has body data, decode it
    body = payload.get("body", {})
    if body.get("data"):
        return decode_gmail_body(body["data"])

    # If the payload has parts, search through them
    parts = payload.get("parts", [])

    # First pass: look for text/plain
    for part in parts:
        mime_type = part.get("mimeType", "")

        if mime_type == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return decode_gmail_body(data)

        # Recursively check nested parts (multipart/alternative, multipart/mixed)
        if part.get("parts"):
            result = extract_gmail_text(part)
            if result:
                return result

    # Second pass: fallback to text/html if no plain text found
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                return decode_gmail_body(data)

    return ""


def extract_gmail_headers(payload: dict) -> dict:
    """
    Extract common email headers from a Gmail message payload.

    Pulls out From, To, Subject, and Date headers into a clean dictionary.

    Args:
        payload: The 'payload' object from a Gmail message response.

    Returns:
        dict: Dictionary with keys: from, to, subject, date.
    """
    headers = payload.get("headers", [])
    result = {
        "from": "",
        "to": "",
        "subject": "",
        "date": "",
    }

    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        if name == "from":
            result["from"] = value
        elif name == "to":
            result["to"] = value
        elif name == "subject":
            result["subject"] = value
        elif name == "date":
            result["date"] = value

    return result


def extract_google_doc_text(document: dict) -> str:
    """
    Extract plain text content from a Google Docs API document response.

    Google Docs API returns a nested structure:
      body → content[] → paragraph → elements[] → textRun → content

    This function walks that structure and concatenates all text runs.

    Args:
        document: The full document response from Google Docs API.

    Returns:
        str: Concatenated plain text content of the document.
    """
    text_parts = []

    body = document.get("body", {})
    content = body.get("content", [])

    for element in content:
        paragraph = element.get("paragraph", {})
        elements = paragraph.get("elements", [])

        for text_element in elements:
            text_run = text_element.get("textRun", {})
            text = text_run.get("content", "")
            if text:
                text_parts.append(text)

    return "".join(text_parts)


def format_sheet_values(values: list | None) -> list[dict]:
    """
    Convert raw Google Sheets values into a clean JSON-friendly format.

    The Sheets API returns values as a list of rows (each row is a list of cell strings).
    This function treats the first row as column headers and converts subsequent rows
    into dictionaries keyed by those headers.

    Example:
        Input:  [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]
        Output: [{"Name": "Alice", "Age": "30"}, {"Name": "Bob", "Age": "25"}]

    Args:
        values: List of rows from Google Sheets API. First row is treated as headers.

    Returns:
        list[dict]: List of row dictionaries. Returns empty list if no data or headers only.
    """
    if not values or len(values) < 2:
        return []

    headers = values[0]
    rows = values[1:]

    result = []
    for row in rows:
        row_dict = {}
        for i, header in enumerate(headers):
            # Handle rows that may have fewer cells than headers
            row_dict[header] = row[i] if i < len(row) else ""
        result.append(row_dict)

    return result
