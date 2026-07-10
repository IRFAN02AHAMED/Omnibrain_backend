from app.ai.openai_brain import OpenAIBrainError, synthesize_brain_answer
from app.ai.graph.brain.nodes import registry
from app.ai.graph.brain.nodes._helpers import unique_source_ids
from app.ai.graph.brain.state import BrainGraphState
from app.core.logger import logger


@registry.register("synthesize_answer")
async def synthesize_answer_node(state: BrainGraphState) -> BrainGraphState:
    output_payload = await _synthesize_with_fallback(state)

    output = {
        **state.get("output", {}),
        "answer": output_payload["answer"],
        "citations": output_payload["citations"],
        "confidence": output_payload["confidence"],
    }
    logger.info("[BrainGraph] Synthesized response with confidence=%.2f", output_payload["confidence"])
    return {**state, "output": output}


async def _synthesize_with_fallback(state: BrainGraphState) -> dict:
    ranked_chunks = state.get("retrieval", {}).get("ranked_chunks", [])
    story_graph = state.get("output", {}).get("story_graph")
    fallback = _fallback_synthesis(state)

    try:
        raw_response = await synthesize_brain_answer(
            query=state["query"],
            chunks=ranked_chunks,
            story_graph=story_graph,
        )
        citations = raw_response.get("citations")
        if not isinstance(citations, list):
            citations = fallback["citations"]
        confidence = raw_response.get("confidence", fallback["confidence"])
        if not isinstance(confidence, (float, int)):
            confidence = fallback["confidence"]
        answer = raw_response.get("answer") or fallback["answer"]
        return {
            "answer": answer,
            "citations": citations,
            "confidence": float(confidence),
        }
    except OpenAIBrainError as exc:
        logger.warning("[BrainGraph] OpenAI synthesis fallback: %s", exc)
        return fallback


def _fallback_synthesis(state: BrainGraphState) -> dict:
    ranked_chunks = state.get("retrieval", {}).get("ranked_chunks", [])
    citations = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "source_type": chunk.get("source_type"),
            "source_id": chunk.get("source_id"),
            "source_url": chunk.get("source_url"),
        }
        for chunk in ranked_chunks[:3]
    ]

    if ranked_chunks:
        answer = (
            f"Found {len(ranked_chunks)} relevant chunk(s) for '{state['query']}'. "
            f"Top evidence comes from {', '.join(unique_source_ids(ranked_chunks[:3]))}."
        )
        confidence = min(0.55 + (0.08 * len(citations)), 0.95)
    else:
        answer = f"No linked evidence was found for '{state['query']}'."
        confidence = 0.2

    return {
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
    }
