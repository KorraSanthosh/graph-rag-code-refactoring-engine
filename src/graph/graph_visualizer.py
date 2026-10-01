import logging

import networkx as nx
from pyvis.network import Network

logger = logging.getLogger(__name__)

CLASS_COLOR = "#e94560"
FUNCTION_COLOR = "#0f3460"


class GraphVisualizer:
    """Renders a dependency graph as an interactive pyvis HTML page."""

    def to_html(self, graph: nx.DiGraph, title: str = "Dependency Graph") -> str:
        """Returns the full HTML string for the graph."""
        net = Network(
            height="100vh", width="100%", directed=True, cdn_resources="in_line",
            bgcolor="#0f0f23", font_color="white", heading="",
        )
        net.barnes_hut(gravity=-6000, central_gravity=0.6, spring_length=120)
        for node, data in graph.nodes(data=True):
            is_class = data.get("type") == "class"
            net.add_node(
                str(node), label=str(node), title=f"{data.get('type', 'unknown')}: {node}",
                color={"background": CLASS_COLOR if is_class else FUNCTION_COLOR, "border": "#6c63ff"},
                borderWidth=2,
                size=30 if is_class else 20,
            )
        for u, v, data in graph.edges(data=True):
            net.add_edge(str(u), str(v), title=data.get("relation", "CALLS"), arrows="to", color="#8b8ba7")
        html = net.generate_html()
        # Full-bleed dark page without pyvis's default card chrome.
        style = "<style>html,body{margin:0;height:100%;background:#0f0f23}.card{border:0!important}#mynetwork{border:0!important}</style>"
        fit = "<script>window.addEventListener('load',function(){setTimeout(function(){network.fit()},1200)})</script>"
        html = html.replace("</body>", fit + "</body>", 1)
        return html.replace("</head>", style + "</head>", 1).replace("<title></title>", f"<title>{title}</title>")
