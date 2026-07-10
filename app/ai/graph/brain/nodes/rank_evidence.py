from app.ai.graph.brain.nodes import registry
from app.ai.graph.brain.state import BrainGraphState
from app.core.config import settings
from app.core.logger import logger


@registry.register("rank_evidence")
def rank_evidence_node(state: BrainGraphState) -> BrainGraphState:
    retrieval = state.get("retrieval", {})
    linked_chunks = retrieval.get("linked_chunks") or retrieval.get("retrieved_chunks", [])

    ranked_chunks = sorted(
        linked_chunks,
        key=lambda chunk: (
            chunk.get("score", 0.0),
            len(chunk.get("entity_ids", [])),
        ),
        reverse=True,
    )[: settings.BRAIN_GRAPH_RANK_LIMIT]

    logger.info("[BrainGraph] Ranked %s chunk(s)", len(ranked_chunks))
    return {
        **state,
        "retrieval": {
            **retrieval,
            "ranked_chunks": ranked_chunks,
        },
    }
