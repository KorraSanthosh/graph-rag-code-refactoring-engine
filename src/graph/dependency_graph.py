import logging
import networkx as nx

logger = logging.getLogger(__name__)


class DependencyGraph:
    """
    Constructs a directed dependency graph from parsed code metadata.
    Nodes represent functions and classes; edges represent CALLS relationships.
    Supports BFS traversal and ancestor lookup for Graph-RAG context retrieval.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_metadata(self, metadata: dict) -> None:
        """Adds nodes for functions/classes and edges for call relationships."""
        for cls in metadata["classes"]:
            self.graph.add_node(cls, type="class")

        for func in metadata["functions"]:
            self.graph.add_node(func, type="function")

        for caller, callee in metadata["calls"]:
            if caller != "global" and self.graph.has_node(callee):
                self.graph.add_edge(caller, callee, relation="CALLS")

        logger.info(
            f"Graph built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges."
        )

    def get_related_nodes(self, node_name: str, depth: int = 2) -> list[str]:
        """
        Retrieves related nodes using BFS (successors) + ancestor lookup.
        Returns empty list if node not found.
        """
        if node_name not in self.graph:
            logger.warning(f"Node '{node_name}' not found in graph.")
            return []

        # Successors within BFS depth (what this node calls)
        lengths = nx.single_source_shortest_path_length(self.graph, node_name, cutoff=depth)
        related: set[str] = {node for node, dist in lengths.items() if dist > 0}

        # Ancestors (what calls this node)
        related.update(nx.ancestors(self.graph, node_name))
        related.discard(node_name)

        return sorted(related)

    def get_subgraph(self, node_name: str, depth: int = 2) -> nx.DiGraph:
        """Returns a subgraph around the target node for visualization."""
        nodes = self.get_related_nodes(node_name, depth) + [node_name]
        return self.graph.subgraph(nodes)

    def to_dict(self) -> dict:
        """Serializes graph to a JSON-compatible dict for API responses."""
        return {
            "nodes": [
                {"id": n, "type": d.get("type", "unknown")}
                for n, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "relation": d.get("relation", "CALLS")}
                for u, v, d in self.graph.edges(data=True)
            ],
        }

    def print_graph(self) -> None:
        print("Nodes:", self.graph.nodes(data=True))
        print("Edges:", self.graph.edges(data=True))
