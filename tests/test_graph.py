import pytest
from src.graph.dependency_graph import DependencyGraph


@pytest.fixture
def sample_metadata():
    return {
        "classes": ["MyClass"],
        "functions": ["process_data", "helper_one", "helper_two", "MyClass.method"],
        "calls": [
            ("process_data", "helper_one"),
            ("process_data", "helper_two"),
            ("MyClass.method", "helper_one"),
        ],
    }


@pytest.fixture
def graph(sample_metadata):
    dg = DependencyGraph()
    dg.build_from_metadata(sample_metadata)
    return dg


# ─── Node Tests ────────────────────────────────────────────────────────────────

def test_nodes_added(graph):
    assert "process_data" in graph.graph.nodes
    assert "helper_one" in graph.graph.nodes
    assert "MyClass" in graph.graph.nodes


def test_node_types(graph):
    assert graph.graph.nodes["MyClass"]["type"] == "class"
    assert graph.graph.nodes["process_data"]["type"] == "function"


# ─── Edge Tests ────────────────────────────────────────────────────────────────

def test_edges_added(graph):
    assert graph.graph.has_edge("process_data", "helper_one")
    assert graph.graph.has_edge("process_data", "helper_two")


def test_no_self_loop(graph):
    assert not graph.graph.has_edge("process_data", "process_data")


# ─── Related Nodes Tests ───────────────────────────────────────────────────────

def test_related_nodes_successors(graph):
    related = graph.get_related_nodes("process_data")
    assert "helper_one" in related
    assert "helper_two" in related


def test_related_nodes_ancestors(graph):
    """helper_one is called by process_data — process_data should appear as ancestor."""
    related = graph.get_related_nodes("helper_one")
    assert "process_data" in related


def test_target_not_in_related(graph):
    """The target node itself should NOT appear in its own related set."""
    related = graph.get_related_nodes("process_data")
    assert "process_data" not in related


def test_unknown_node_returns_empty(graph):
    assert graph.get_related_nodes("nonexistent_function") == []


# ─── Serialization Tests ───────────────────────────────────────────────────────

def test_to_dict_has_nodes_and_edges(graph):
    d = graph.to_dict()
    assert "nodes" in d
    assert "edges" in d
    assert len(d["nodes"]) > 0
    assert len(d["edges"]) > 0


def test_to_dict_node_has_id_and_type(graph):
    d = graph.to_dict()
    for node in d["nodes"]:
        assert "id" in node
        assert "type" in node


# ─── Empty Graph Tests ─────────────────────────────────────────────────────────

def test_empty_metadata_builds_empty_graph():
    dg = DependencyGraph()
    dg.build_from_metadata({"classes": [], "functions": [], "calls": []})
    assert dg.graph.number_of_nodes() == 0
    assert dg.graph.number_of_edges() == 0
