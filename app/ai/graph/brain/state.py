from typing import Any, Literal, NotRequired, TypedDict


IntentType = Literal["simple_lookup", "cross_source_story"]
SourceType = Literal["github", "jira", "gdrive", "notes"]


class ChunkMetadata(TypedDict, total=False):
    source_type: SourceType
    source_subtype: str
    source_id: str
    source_url: str
    title: str
    entity_ids: list[str]
    project_id: str
    feature_id: str
    author: str
    status: str
    priority: str
    labels: list[str]
    timestamp: str
    relationship_hints: dict[str, Any]


class RetrievedChunk(TypedDict, total=False):
    chunk_id: int
    document_id: int
    chunk_text: str
    score: float
    source_type: str
    source_subtype: str
    source_id: str
    source_url: str
    title: str
    entity_ids: list[str]
    project_id: str
    timestamp: str
    metadata: ChunkMetadata


class RouteState(TypedDict, total=False):
    intent: IntentType
    source_hint: str | None
    entities: list[str]
    keywords: list[str]
    needs_story_graph: bool
    time_hint: str | None


class RetrievalState(TypedDict, total=False):
    top_k: int
    metadata_filter: dict[str, Any]
    retrieved_chunks: list[RetrievedChunk]
    linked_chunks: list[RetrievedChunk]
    ranked_chunks: list[RetrievedChunk]


class LinkingState(TypedDict, total=False):
    linked_entity_ids: list[str]
    relationships: list[dict[str, Any]]


class OutputState(TypedDict, total=False):
    answer: str
    citations: list[dict[str, Any]]
    confidence: float
    story_graph: dict[str, Any] | None
    mermaid: str | None
    sources: list[dict[str, Any]]
    has_story_graph: bool


class BrainGraphState(TypedDict):
    query: str
    user_id: int
    session_id: int

    route: NotRequired[RouteState]
    retrieval: NotRequired[RetrievalState]
    linking: NotRequired[LinkingState]
    output: NotRequired[OutputState]
    errors: NotRequired[list[str]]
