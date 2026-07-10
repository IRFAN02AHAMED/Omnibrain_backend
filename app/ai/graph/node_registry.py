from typing import Callable


class NodeRegistry:
    """Registry for graph node functions."""

    def __init__(self):
        self._nodes: dict[str, Callable] = {}

    def register(self, name: str | None = None):
        def decorator(func: Callable) -> Callable:
            node_name = name or func.__name__.replace("_node", "")
            self._nodes[node_name] = func
            return func

        return decorator

    def get(self, name: str) -> Callable:
        return self._nodes[name]

    def all(self) -> dict[str, Callable]:
        return dict(self._nodes)

    def names(self) -> list[str]:
        return list(self._nodes.keys())
