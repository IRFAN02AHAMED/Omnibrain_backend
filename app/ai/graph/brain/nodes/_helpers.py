import re
from collections import defaultdict
from typing import Any

from app.ai.graph.brain.state import RetrievedChunk


ENTITY_PATTERN = re.compile(r"\b(?:JIRA-\d+|PR-\d+|DOC-\d+|NOTE-\d+|FEATURE-[A-Z0-9-]+)\b")


def extract_source_hint(lowered_query: str) -> str | None:
    source_keywords = {
        "github": "github",
        "jira": "jira",
        "drive": "gdrive",
        "document": "gdrive",
        "doc": "gdrive",
        "note": "notes",
    }
    for keyword, source_type in source_keywords.items():
        if keyword in lowered_query:
            return source_type
    return None


def extract_keywords(query: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]+", query)
    stop_words = {"what", "tell", "show", "about", "with", "from", "into", "this"}
    return [word.lower() for word in words if word.lower() not in stop_words][:8]


def build_stub_chunks(query: str, entity_ids: list[str], source_hint: str | None) -> list[RetrievedChunk]:
    default_entity = entity_ids[0] if entity_ids else "JIRA-123"
    source_type = source_hint or "jira"
    return [
        {
            "chunk_id": 1,
            "document_id": 101,
            "chunk_text": f"Primary evidence for query '{query}' tied to {default_entity}.",
            "score": 0.89,
            "source_type": source_type,
            "source_subtype": "ticket" if source_type == "jira" else "doc",
            "source_id": default_entity if source_type == "jira" else "DOC-12",
            "source_url": f"https://example.com/{source_type}/{default_entity.lower()}",
            "title": f"{default_entity} source context",
            "entity_ids": entity_ids or [default_entity],
            "project_id": "OMNIBRAIN",
            "timestamp": "2026-07-10T10:00:00Z",
            "metadata": {
                "source_type": source_type,  # type: ignore[typeddict-item]
                "source_subtype": "ticket" if source_type == "jira" else "doc",
                "source_id": default_entity if source_type == "jira" else "DOC-12",
                "source_url": f"https://example.com/{source_type}/{default_entity.lower()}",
                "title": f"{default_entity} source context",
                "entity_ids": entity_ids or [default_entity],
                "project_id": "OMNIBRAIN",
                "timestamp": "2026-07-10T10:00:00Z",
            },
        }
    ]


def build_linked_stub_chunks(entity_ids: list[str]) -> list[RetrievedChunk]:
    if not entity_ids:
        return []

    primary_entity = entity_ids[0]
    return [
        {
            "chunk_id": 2,
            "document_id": 202,
            "chunk_text": f"GitHub PR-45 implements {primary_entity}.",
            "score": 0.84,
            "source_type": "github",
            "source_subtype": "pull_request",
            "source_id": "PR-45",
            "source_url": "https://example.com/github/pr-45",
            "title": "Implementation PR",
            "entity_ids": [primary_entity, "PR-45", "FEATURE-SEARCH-01"],
            "project_id": "OMNIBRAIN",
            "timestamp": "2026-07-10T11:00:00Z",
        },
        {
            "chunk_id": 3,
            "document_id": 303,
            "chunk_text": f"Drive doc DOC-12 describes {primary_entity} rollout.",
            "score": 0.79,
            "source_type": "gdrive",
            "source_subtype": "doc",
            "source_id": "DOC-12",
            "source_url": "https://example.com/gdrive/doc-12",
            "title": "Design notes",
            "entity_ids": [primary_entity, "DOC-12", "FEATURE-SEARCH-01"],
            "project_id": "OMNIBRAIN",
            "timestamp": "2026-07-10T12:00:00Z",
        },
    ]


def build_relationships(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    for chunk in chunks:
        entity_ids = chunk.get("entity_ids", [])
        if len(entity_ids) < 2:
            continue
        anchor = entity_ids[0]
        for related_entity in entity_ids[1:]:
            relationships.append(
                {
                    "from": anchor,
                    "to": related_entity,
                    "relation": "related_to",
                    "source_type": chunk.get("source_type"),
                }
            )
    return relationships


def dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[tuple[Any, ...]] = set()
    unique_chunks: list[RetrievedChunk] = []
    for chunk in chunks:
        key = (
            chunk.get("chunk_id"),
            chunk.get("source_type"),
            chunk.get("source_id"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_chunks.append(chunk)
    return unique_chunks


def unique_source_ids(chunks: list[RetrievedChunk]) -> list[str]:
    source_ids: list[str] = []
    seen = set()
    for chunk in chunks:
        source_id = chunk.get("source_id")
        if source_id and source_id not in seen:
            source_ids.append(source_id)
            seen.add(source_id)
    return source_ids


def build_mermaid(story_graph: dict[str, Any]) -> str:
    lines = ["graph TD"]
    label_lookup: dict[str, str] = defaultdict(str)

    for node in story_graph.get("nodes", []):
        label_lookup[node["id"]] = node.get("label", node["id"])
        lines.append(f'    {node["id"]}["{label_lookup[node["id"]]}"]')

    for edge in story_graph.get("edges", []):
        lines.append(f'    {edge["from"]} -->|{edge["relation"]}| {edge["to"]}')

    return "\n".join(lines)


def normalize_story_graph(raw_graph: dict[str, Any], default_root: str | None) -> dict[str, Any]:
    nodes = raw_graph.get("nodes", [])
    edges = raw_graph.get("edges", [])
    return {
        "root": raw_graph.get("root") or default_root,
        "nodes": [node for node in nodes if isinstance(node, dict) and node.get("id")],
        "edges": [
            edge
            for edge in edges
            if isinstance(edge, dict) and edge.get("from") and edge.get("to")
        ],
    }
