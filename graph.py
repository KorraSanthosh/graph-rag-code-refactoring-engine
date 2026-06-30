import networkx as nx

class DependencyGraph:
    """Constructs a dependency graph using functions and classes as nodes."""
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_metadata(self, metadata: dict):
        """Adds nodes for functions/classes and edges for calls/imports."""
        # Add Nodes
        for cls in metadata["classes"]:
            self.graph.add_node(cls, type="class")
        
        for func in metadata["functions"]:
            # Avoid duplicate nodes if method has same name as a global function
            self.graph.add_node(func, type="function")

        # Add Edges (CALLS)
        for caller, callee in metadata["calls"]:
            if caller != "global" and self.graph.has_node(callee):
                self.graph.add_edge(caller, callee, relation="CALLS")

    def get_related_nodes(self, node_name: str, depth: int = 2):
        """Retrieves related nodes (dependencies) using BFS."""
        if node_name not in self.graph:
            return []
        
        # Get all nodes reachable within 'depth' steps
        lengths = nx.single_source_shortest_path_length(self.graph, node_name, cutoff=depth)
        related = {node for node, dist in lengths.items() if dist > 0}
        # Also get ancestors (things that call this)
        related.update(nx.ancestors(self.graph, node_name))
        related.discard(node_name)
        
        return list(related)

    def print_graph(self):
        print("Graph Nodes:", self.graph.nodes(data=True))
        print("Graph Edges:", self.graph.edges())
