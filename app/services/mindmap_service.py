from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_brain import OpenAIBrainError, generate_document_mindmap
from app.core.logger import logger
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository


async def generate_mindmap_for_document(
    user_id: int,
    document_id: int,
    db: AsyncSession,
    max_depth: int = 3,
    max_branches_per_node: int = 5,
) -> dict[str, Any]:
    doc_repo = DocumentRepository(db)
    chunk_repo = DocumentChunkRepository(db)

    document = await doc_repo.get_by_owner_and_id(user_id, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    chunks = await chunk_repo.get_by_document_id(document.id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document has no embedded chunks yet. Sync or reprocess the document first.",
        )

    context_chunks = chunks[:12]
    document_text = "\n\n".join(
        f"[chunk-{chunk.chunk_index + 1}] {chunk.chunk_text.strip()}"
        for chunk in context_chunks
        if chunk.chunk_text
    )[:16000]

    try:
        raw_mindmap = await generate_document_mindmap(
            document_name=document.original_file_name or document.file_name,
            document_text=document_text,
            max_depth=max_depth,
            max_branches_per_node=max_branches_per_node,
        )
        root = _normalize_node(raw_mindmap.get("root"), fallback_label=_derive_title(document))
        title = raw_mindmap.get("title") or _derive_title(document)
    except OpenAIBrainError as exc:
        logger.warning("[MindMap] OpenAI generation failed for document_id=%s error=%s", document_id, exc)
        title = _derive_title(document)
        root = _build_fallback_mindmap_root(title, context_chunks)
    except Exception as exc:
        logger.exception("[MindMap] Unexpected generation error for document_id=%s", document_id)
        title = _derive_title(document)
        root = _build_fallback_mindmap_root(title, context_chunks)

    return {
        "mindmap_id": f"mindmap-{document.id}-{uuid.uuid4().hex[:8]}",
        "document_id": str(document.id),
        "document_name": document.original_file_name or document.file_name,
        "title": title,
        "source_count": 1,
        "root": root,
    }


def _normalize_node(raw_node: dict[str, Any] | None, fallback_label: str, depth: int = 0) -> dict[str, Any]:
    if not isinstance(raw_node, dict):
        return {
            "id": "root" if depth == 0 else f"node-{uuid.uuid4().hex[:8]}",
            "label": fallback_label,
            "summary": "",
            "has_children": False,
            "source_reference": None,
            "children": [],
        }

    normalized_children = [
        _normalize_node(child, fallback_label=(child or {}).get("label") or "Topic", depth=depth + 1)
        for child in (raw_node.get("children") or [])
        if isinstance(child, dict)
    ]

    node_id = raw_node.get("id") or ("root" if depth == 0 else f"node-{uuid.uuid4().hex[:8]}")
    label = raw_node.get("label") or fallback_label
    summary = raw_node.get("summary") or ""
    source_reference = raw_node.get("source_reference")
    if not isinstance(source_reference, dict):
        source_reference = None

    return {
        "id": _slugify_id(node_id),
        "label": label,
        "summary": summary,
        "has_children": bool(raw_node.get("has_children") or normalized_children),
        "source_reference": source_reference,
        "children": normalized_children,
    }


def _build_fallback_mindmap_root(title: str, chunks: list[Any]) -> dict[str, Any]:
    children = []
    for chunk in chunks[:5]:
        summary = _first_sentence(chunk.chunk_text)
        label = _guess_chunk_label(chunk.chunk_text, chunk.chunk_index + 1)
        children.append(
            {
                "id": f"topic-{chunk.chunk_index + 1}",
                "label": label,
                "summary": summary,
                "has_children": False,
                "source_reference": {
                    "chunk_id": f"chunk-{chunk.chunk_index + 1}",
                    "section": label,
                    "page": chunk.page_number,
                },
                "children": [],
            }
        )

    return {
        "id": "root",
        "label": title,
        "summary": f"Mind map generated from {len(chunks)} document chunks.",
        "has_children": bool(children),
        "source_reference": None,
        "children": children,
    }


def _derive_title(document: Any) -> str:
    raw_name = document.original_file_name or document.file_name or "Document"
    base = raw_name.rsplit(".", 1)[0]
    cleaned = re.sub(r"[_-]+", " ", base).strip()
    return cleaned.title() if cleaned else "Document Mind Map"


def _first_sentence(text: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if not cleaned:
        return "No summary available."
    sentence = re.split(r"(?<=[.!?])\s+", cleaned)[0]
    return sentence[:220]


def _guess_chunk_label(text: str | None, index: int) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if not cleaned:
        return f"Topic {index}"
    words = cleaned.split()[:5]
    return " ".join(words).strip(" .,:;") or f"Topic {index}"


def _slugify_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    return slug or f"node-{uuid.uuid4().hex[:8]}"
