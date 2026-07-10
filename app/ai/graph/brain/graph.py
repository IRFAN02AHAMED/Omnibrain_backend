from functools import partial

from app.ai.graph.brain import edges
from app.ai.graph.brain.nodes import registry


def build_brain_graph():
    """Build the knowledge-brain LangGraph workflow."""
    try:
        from langgraph.graph import END, StateGraph

        from app.ai.graph.brain.state import BrainGraphState

        workflow = StateGraph(BrainGraphState)

        for name, func in registry.all().items():
            workflow.add_node(name, partial(func))

        workflow.set_entry_point("route_query")
        workflow.add_edge("route_query", "retrieval")
        workflow.add_edge("retrieval", "entity_linking")
        workflow.add_edge("entity_linking", "rank_evidence")
        workflow.add_conditional_edges(
            "rank_evidence",
            edges.route_after_rank,
            {
                "story_graph": "build_story_graph",
                "synthesis": "synthesize_answer",
            },
        )
        workflow.add_edge("build_story_graph", "synthesize_answer")
        workflow.add_edge("synthesize_answer", "format_response")
        workflow.add_edge("format_response", END)

        return workflow.compile()
    except ImportError:
        return None
