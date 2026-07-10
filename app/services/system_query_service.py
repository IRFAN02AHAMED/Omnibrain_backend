import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_brain import OpenAIBrainError, interpret_system_query
from app.models.chat_session import ChatSession
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.session_document import SessionDocument
from app.core.logger import logger


class SystemQueryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_context_for_query(
        self,
        user_id: int,
        session_id: int,
        query: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        normalized_query = (query or "").lower().strip()
        parsed_query = await self._interpret_query(query, conversation_history or [])
        if not parsed_query.get("is_system_query") and not self._is_system_query(normalized_query):
            return ""

        documents = await self._get_user_documents(user_id)
        session_documents = await self._get_session_documents(user_id, session_id)
        total_chunks = await self._get_global_chunk_count(user_id)
        total_sessions = await self._get_chat_session_count(user_id)

        matched_documents = self._match_documents_from_query(
            normalized_query,
            parsed_query.get("document_names") or [],
            documents,
            session_documents,
        )
        if not matched_documents and (
            parsed_query.get("time_reference") == "upload_time"
            or self._is_upload_time_query(normalized_query)
        ):
            matched_documents = self._resolve_documents_from_scope(
                parsed_query=parsed_query,
                documents=documents,
                session_documents=session_documents,
            )
        if matched_documents and (
            parsed_query.get("time_reference") == "upload_time"
            or self._is_upload_time_query(normalized_query)
        ):
            lines = ["System KB metadata:"]
            for matched_document in matched_documents:
                uploaded_at = matched_document.get("uploaded_at") or matched_document.get("created_at")
                lines.append(
                    f"- {matched_document.get('original_file_name') or matched_document.get('file_name')} | "
                    f"uploaded at: {uploaded_at or 'Unknown'} | "
                    f"status: {matched_document.get('processing_status') or 'Unknown'} | "
                    f"chunks: {matched_document.get('chunk_count') or 0}"
                )
            return "\n".join(lines)

        recent_documents = documents[:5]
        lines = [
            "System KB metadata:",
            f"- Total global documents in KB: {len(documents)}",
            f"- Total session documents in this chat: {len(session_documents)}",
            f"- Total embedded global chunks: {total_chunks}",
            f"- Total chat sessions for this user: {total_sessions}",
        ]

        if recent_documents:
            lines.append("- Recent global documents:")
            for document in recent_documents:
                uploaded_at = document.get("uploaded_at") or document.get("created_at") or "Unknown"
                lines.append(
                    f"  - {document.get('original_file_name') or document.get('file_name')} | "
                    f"uploaded: {uploaded_at} | chunks: {document.get('chunk_count') or 0} | "
                    f"status: {document.get('processing_status') or 'Unknown'}"
                )

        if session_documents:
            lines.append("- Current chat documents:")
            for document in session_documents[:5]:
                uploaded_at = document.get("uploaded_at") or document.get("created_at") or "Unknown"
                lines.append(
                    f"  - {document.get('original_file_name') or document.get('file_name')} | "
                    f"uploaded: {uploaded_at} | chunks: {document.get('chunk_count') or 0}"
                )

        return "\n".join(lines)

    def _resolve_documents_from_scope(
        self,
        parsed_query: dict,
        documents: list[dict],
        session_documents: list[dict],
    ) -> list[dict]:
        scope = parsed_query.get("scope") or "all"
        wants_each = bool(parsed_query.get("wants_each"))
        query_type = parsed_query.get("query_type")

        if scope == "session":
            candidates = session_documents
        elif scope == "global":
            candidates = documents
        else:
            candidates = session_documents or documents

        if not candidates:
            return []

        if wants_each or query_type == "document_upload_time":
            return candidates[:10]

        return candidates[:1]

    async def _interpret_query(self, query: str, conversation_history: list[dict]) -> dict:
        fallback = {
            "is_system_query": self._is_system_query((query or "").lower()),
            "query_type": "unknown",
            "scope": "all",
            "document_names": [],
            "wants_each": False,
            "time_reference": "upload_time" if self._is_upload_time_query((query or "").lower()) else None,
        }
        try:
            parsed = await interpret_system_query(query=query, conversation_history=conversation_history)
            if isinstance(parsed, dict):
                return {
                    **fallback,
                    **parsed,
                    "document_names": [name for name in (parsed.get("document_names") or []) if isinstance(name, str)],
                }
        except OpenAIBrainError as exc:
            logger.warning("[SystemQuery] LLM parser fallback for query=%s error=%s", query, exc)
        return fallback

    def _is_system_query(self, normalized_query: str) -> bool:
        kb_keywords = [
            "how many documents",
            "how many docs",
            "documents are there",
            "docs are there",
            "in the kb",
            "in kb",
            "knowledge base",
            "uploaded",
            "upload date",
            "when was",
            "how many chunks",
            "how many files",
            "what documents do we have",
            "what docs do we have",
            "recent documents",
            "recent uploads",
        ]
        system_targets = ["kb", "knowledge base", "document", "documents", "docs", "files", "chunks", "uploaded"]
        return any(keyword in normalized_query for keyword in kb_keywords) and any(
            target in normalized_query for target in system_targets
        )

    def _is_upload_time_query(self, normalized_query: str) -> bool:
        return any(phrase in normalized_query for phrase in ["when was", "when did", "uploaded", "upload date"])

    async def _get_user_documents(self, user_id: int) -> list[dict]:
        stmt = (
            select(Document)
            .where(Document.owner_id == user_id, Document.is_active == True)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        documents = result.scalars().all()
        return [self._serialize_document(document) for document in documents]

    async def _get_session_documents(self, user_id: int, session_id: int) -> list[dict]:
        if not session_id:
            return []

        stmt = (
            select(SessionDocument)
            .where(
                SessionDocument.owner_id == user_id,
                SessionDocument.session_id == session_id,
                SessionDocument.is_active == True,
            )
            .order_by(SessionDocument.created_at.desc())
        )
        result = await self.db.execute(stmt)
        documents = result.scalars().all()
        return [self._serialize_document(document) for document in documents]

    async def _get_global_chunk_count(self, user_id: int) -> int:
        stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.owner_id == user_id,
            DocumentChunk.is_active == True,
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def _get_chat_session_count(self, user_id: int) -> int:
        stmt = select(func.count(ChatSession.id)).where(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True,
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    def _match_documents_from_query(
        self,
        normalized_query: str,
        parsed_document_names: list[str],
        *document_lists: list[dict],
    ) -> list[dict]:
        matched: list[dict] = []
        compact_query = re.sub(r"[^a-z0-9]+", "", normalized_query)
        compact_names = [
            re.sub(r"[^a-z0-9]+", "", document_name.lower())
            for document_name in parsed_document_names
            if document_name
        ]
        for documents in document_lists:
            for document in documents:
                name = document.get("original_file_name") or document.get("file_name") or ""
                compact_name = re.sub(r"[^a-z0-9]+", "", name.lower())
                if not compact_name:
                    continue
                if compact_name in compact_query or any(parsed_name and (compact_name in parsed_name or parsed_name in compact_name) for parsed_name in compact_names):
                    if document not in matched:
                        matched.append(document)
        return matched

    def _serialize_document(self, document) -> dict:
        return {
            "id": document.id,
            "file_name": document.file_name,
            "original_file_name": getattr(document, "original_file_name", None),
            "processing_status": getattr(document, "processing_status", None),
            "chunk_count": getattr(document, "chunk_count", 0),
            "uploaded_at": document.uploaded_at.isoformat() if getattr(document, "uploaded_at", None) else None,
            "created_at": document.created_at.isoformat() if getattr(document, "created_at", None) else None,
        }
