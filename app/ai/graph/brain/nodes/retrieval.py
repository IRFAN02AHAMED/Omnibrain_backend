from app.ai.graph.brain.nodes import registry
from app.ai.graph.brain.nodes._helpers import build_stub_chunks
from app.ai.graph.brain.state import BrainGraphState
from app.core.config import settings
from app.core.logger import logger


@registry.register("retrieval")
async def retrieval_node(state: BrainGraphState) -> BrainGraphState:
    route = state.get("route", {})
    source_hint = route.get("source_hint")
    retrieved_chunks = build_stub_chunks(state["query"], route.get("entities", []), source_hint)

    retrieval_state = {
        "top_k": settings.BRAIN_GRAPH_TOP_K,
        "metadata_filter": {"source_type": source_hint} if source_hint else {},
        "retrieved_chunks": retrieved_chunks,
        "linked_chunks": [],
        "ranked_chunks": [],
    }
    logger.info("[BrainGraph] Retrieved %s primary chunk(s)", len(retrieved_chunks))
    return {**state, "retrieval": retrieval_state}
