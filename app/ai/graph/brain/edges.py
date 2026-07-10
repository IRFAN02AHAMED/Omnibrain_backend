from app.ai.graph.brain.state import BrainGraphState


def route_after_rank(state: BrainGraphState) -> str:
    intent = state.get("route", {}).get("intent", "simple_lookup")
    return "story_graph" if intent == "cross_source_story" else "synthesis"
