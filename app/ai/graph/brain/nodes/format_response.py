from app.ai.graph.brain.nodes import registry
from app.ai.graph.brain.state import BrainGraphState


@registry.register("format_response")
def format_response_node(state: BrainGraphState) -> BrainGraphState:
    output = state.get("output", {})
    formatted_output = {
        **output,
        "sources": output.get("citations", []),
        "has_story_graph": bool(output.get("story_graph")),
    }
    return {**state, "output": formatted_output}
