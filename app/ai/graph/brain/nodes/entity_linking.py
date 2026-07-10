from app.ai.graph.brain.nodes import registry
from app.ai.graph.brain.nodes._helpers import (
    build_linked_stub_chunks,
    build_relationships,
    dedupe_chunks,
)
from app.ai.graph.brain.state import BrainGraphState
from app.core.config import settings
from app.core.logger import logger


@registry.register("entity_linking")
async def entity_linking_node(state: BrainGraphState) -> BrainGraphState:
    retrieval = state.get("retrieval", {})
    retrieved_chunks = retrieval.get("retrieved_chunks", [])

    linked_entity_ids = sorted(
        {
            entity_id
            for chunk in retrieved_chunks
            for entity_id in chunk.get("entity_ids", [])
        }
    )

    linked_chunks = dedupe_chunks(
        [
            *retrieved_chunks,
            *build_linked_stub_chunks(linked_entity_ids),
        ]
    )[: settings.BRAIN_GRAPH_LINK_LIMIT]

    linking_state = {
        "linked_entity_ids": linked_entity_ids,
        "relationships": build_relationships(linked_chunks),
    }
    updated_retrieval = {
        **retrieval,
        "linked_chunks": linked_chunks,
    }

    logger.info(
        "[BrainGraph] Linked %s entity id(s) into %s chunk(s)",
        len(linked_entity_ids),
        len(linked_chunks),
    )
    return {
        **state,
        "retrieval": updated_retrieval,
        "linking": linking_state,
    }
