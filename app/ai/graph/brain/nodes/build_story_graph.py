from typing import Any

from app.ai.openai_brain import OpenAIBrainError, build_story_graph_from_chunks
from app.ai.graph.brain.nodes import registry
from app.ai.graph.brain.nodes._helpers import build_mermaid, normalize_story_graph
from app.ai.graph.brain.state import BrainGraphState
from app.core.logger import logger


@registry.register("build_story_graph")
async def build_story_graph_node(state: BrainGraphState) -> BrainGraphState:
    story_graph = await _build_story_graph_with_fallback(state)

    output = {
        **state.get("output", {}),
        "story_graph": story_graph,
        "mermaid": build_mermaid(story_graph),
    }
    logger.info("[BrainGraph] Built story graph with %s node(s)", len(story_graph["nodes"]))
    return {**state, "output": output}


async def _build_story_graph_with_fallback(state: BrainGraphState) -> dict[str, Any]:
    fallback_graph = _build_story_graph_fallback(state)
    ranked_chunks = state.get("retrieval", {}).get("ranked_chunks", [])
    route_entities = state.get("route", {}).get("entities", [])

    try:
        raw_graph = await build_story_graph_from_chunks(
            query=state["query"],
            entities=route_entities,
            chunks=ranked_chunks,
        )
        return normalize_story_graph(raw_graph, fallback_graph["root"])
    except OpenAIBrainError as exc:
        logger.warning("[BrainGraph] OpenAI story-graph fallback: %s", exc)
        return fallback_graph


def _build_story_graph_fallback(state: BrainGraphState) -> dict[str, Any]:
    ranked_chunks = state.get("retrieval", {}).get("ranked_chunks", [])
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()

    for chunk in ranked_chunks:
        for entity_id in chunk.get("entity_ids", []):
            if entity_id not in seen_node_ids:
                nodes.append(
                    {
                        "id": entity_id,
                        "label": entity_id,
                        "type": chunk.get("source_type", "unknown"),
                    }
                )
                seen_node_ids.add(entity_id)

        entity_ids = chunk.get("entity_ids", [])
        if len(entity_ids) >= 2:
            for left, right in zip(entity_ids, entity_ids[1:]):
                edges.append({"from": left, "to": right, "relation": "related_to"})

    story_graph = {
        "root": (state.get("route", {}).get("entities") or [None])[0],
        "nodes": nodes,
        "edges": edges,
    }
    return story_graph
