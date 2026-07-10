from app.ai.openai_brain import OpenAIBrainError, classify_brain_query
from app.ai.graph.brain.nodes import registry
from app.ai.graph.brain.nodes._helpers import ENTITY_PATTERN, extract_keywords, extract_source_hint
from app.ai.graph.brain.state import BrainGraphState
from app.core.logger import logger


@registry.register("route_query")
async def route_query_node(state: BrainGraphState) -> BrainGraphState:
    query = state["query"]
    route_state = await _route_with_fallback(query)
    logger.info(
        "[BrainGraph] Routed query with intent=%s entities=%s",
        route_state["intent"],
        route_state["entities"],
    )
    return {**state, "route": route_state}


async def _route_with_fallback(query: str) -> dict:
    lowered_query = query.lower()
    fallback = _heuristic_route(query)

    try:
        raw_result = await classify_brain_query(query)
        llm_entities = raw_result.get("entities") or fallback["entities"]
        normalized_entities = _merge_entities(llm_entities, query)
        intent = raw_result.get("intent")
        if intent not in {"simple_lookup", "cross_source_story"}:
            intent = fallback["intent"]

        return {
            "intent": intent,
            "source_hint": raw_result.get("source_hint") or fallback["source_hint"],
            "entities": normalized_entities,
            "keywords": raw_result.get("keywords") or fallback["keywords"],
            "needs_story_graph": bool(raw_result.get("needs_story_graph", intent == "cross_source_story")),
            "time_hint": raw_result.get("time_hint"),
        }
    except OpenAIBrainError as exc:
        logger.warning("[BrainGraph] OpenAI router fallback: %s", exc)
        return fallback


def _heuristic_route(query: str) -> dict:
    lowered_query = query.lower()
    entities = sorted(set(ENTITY_PATTERN.findall(query)))
    story_keywords = {"story", "journey", "timeline", "across", "connect", "relationship"}
    needs_story_graph = any(keyword in lowered_query for keyword in story_keywords) or len(entities) > 1
    intent = "cross_source_story" if needs_story_graph else "simple_lookup"

    return {
        "intent": intent,
        "source_hint": extract_source_hint(lowered_query),
        "entities": entities,
        "keywords": extract_keywords(query),
        "needs_story_graph": needs_story_graph,
        "time_hint": None,
    }


def _merge_entities(candidate_entities: list[str], query: str) -> list[str]:
    extracted_entities = sorted(set(ENTITY_PATTERN.findall(query)))
    cleaned_candidates = [entity for entity in candidate_entities if isinstance(entity, str)]
    return sorted(set(cleaned_candidates) | set(extracted_entities))
