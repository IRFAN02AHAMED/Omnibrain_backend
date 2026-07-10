# app/ai/graph/google_graph.py
# Purpose: Prepare a simple LangGraph structure placeholder for Google connector workflows.
# pip install google-api-python-client google-auth google-auth-oauthlib python-dotenv langgraph langchain-core

from app.ai.graph.google_nodes import (
    list_drive_node,
    search_drive_node,
    list_docs_node,
    read_doc_node,
    list_sheets_node,
    read_sheet_node,
    list_gmail_node,
    read_gmail_node,
)


def build_google_graph():
    """
    Build a simple LangGraph StateGraph for Google connector workflows.

    This is a placeholder skeleton for future AI-powered Google integration.
    Each node wraps a Google service action (Drive, Docs, Sheets, Gmail).

    The graph is not connected to main.py yet. It will be used when
    the AI/LangGraph pipeline is finalized.

    Returns:
        StateGraph | None: A compiled LangGraph if langgraph is available,
                           or None if LangGraph is not installed.

    Usage (future):
        graph = build_google_graph()
        if graph:
            result = graph.invoke({"user_id": 1, "query": "project"})
    """
    try:
        from langgraph.graph import StateGraph, END

        # Define a simple state schema (just a dictionary for now)
        # TODO: Define a proper TypedDict or Pydantic model for state when AI pipeline is finalized.

        graph = StateGraph(dict)

        # ── Register nodes ───────────────────────────────────────────────────
        graph.add_node("list_drive", list_drive_node)
        graph.add_node("search_drive", search_drive_node)
        graph.add_node("list_docs", list_docs_node)
        graph.add_node("read_doc", read_doc_node)
        graph.add_node("list_sheets", list_sheets_node)
        graph.add_node("read_sheet", read_sheet_node)
        graph.add_node("list_gmail", list_gmail_node)
        graph.add_node("read_gmail", read_gmail_node)

        # ── Simple linear edges (placeholder) ───────────────────────────────
        # TODO: Add conditional routing logic when AI pipeline is designed.
        # For now, each node independently goes to END.
        graph.add_edge("list_drive", END)
        graph.add_edge("search_drive", END)
        graph.add_edge("list_docs", END)
        graph.add_edge("read_doc", END)
        graph.add_edge("list_sheets", END)
        graph.add_edge("read_sheet", END)
        graph.add_edge("list_gmail", END)
        graph.add_edge("read_gmail", END)

        # Set a default entry point (can be changed later)
        graph.set_entry_point("list_drive")

        # Compile the graph
        compiled_graph = graph.compile()
        return compiled_graph

    except ImportError:
        # LangGraph is not installed — safe fallback
        # TODO: Install langgraph package to enable AI graph features.
        print(
            "[google_graph] WARNING: langgraph is not installed. "
            "Google AI graph features are disabled. "
            "Install with: pip install langgraph langchain-core"
        )
        return None
    except Exception as e:
        # Catch any other errors to avoid breaking backend startup
        print(f"[google_graph] WARNING: Failed to build Google graph: {e}")
        return None
