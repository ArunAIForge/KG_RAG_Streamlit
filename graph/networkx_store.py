# graph/networkx_store.py
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import networkx as nx

from config.settings import settings
from extraction.schemas import NodeEntity, RelationshipTriple
from graph.base import BaseGraphStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class NetworkXGraphStore(BaseGraphStore):
    """In-memory Directed Multigraph implementation using NetworkX."""

    def __init__(self, persistence_path: Optional[Path] = None):
        self.graph = nx.MultiDiGraph()
        self.persistence_path = persistence_path or (settings.DATA_DIR / "networkx_graph.json")

    def connect(self) -> None:
        """Loads existing graph from JSON disk if available."""
        if self.persistence_path and self.persistence_path.exists():
            try:
                with open(self.persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.graph = nx.node_link_graph(data, edges="edges")
                logger.info(f"Loaded NetworkX graph with {self.graph.number_of_nodes()} nodes.")
            except Exception as e:
                logger.warning(f"Could not load saved NetworkX graph: {e}. Starting with empty graph.")
                self.graph = nx.MultiDiGraph()
        else:
            logger.info("Initialized empty in-memory NetworkX graph.")

    def close(self) -> None:
        """Persists graph to JSON file on disk."""
        if self.persistence_path:
            try:
                data = nx.node_link_data(self.graph, edges="edges")
                with open(self.persistence_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved NetworkX graph to {self.persistence_path}")
            except Exception as e:
                logger.error(f"Failed to persist NetworkX graph: {e}")

    def upsert_node(self, node: NodeEntity) -> None:
        label = node.label.value if hasattr(node.label, "value") else str(node.label)
        node_attrs = {
            "id": node.id,
            "name": node.name,
            "label": label,
            **node.properties
        }
        self.graph.add_node(node.id, **node_attrs)

    def upsert_relationship(self, rel: RelationshipTriple) -> None:
        rel_type = rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type)
        if not self.graph.has_node(rel.source_id) or not self.graph.has_node(rel.target_id):
            logger.warning(f"Cannot add edge: source ({rel.source_id}) or target ({rel.target_id}) does not exist.")
            return

        edge_attrs = {
            "type": rel_type,
            **rel.properties
        }
        self.graph.add_edge(rel.source_id, rel.target_id, key=rel_type, **edge_attrs)

    def query(self, query_str: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Traverses NetworkX graph based on query terms or scheme names.
        """
        if self.graph.number_of_nodes() == 0:
            self.connect()

        params = params or {}
        raw_scheme_name = (params.get("scheme_name") or "").lower().strip()
        raw_keywords = params.get("keywords") or []

        # Tokenize query keywords
        tokens = set()
        if raw_scheme_name:
            for w in re.split(r"\W+", raw_scheme_name):
                if len(w) > 2 and w not in ["the", "for", "and", "scheme"]:
                    tokens.add(w.lower())

        for kw in raw_keywords:
            for w in re.split(r"\W+", str(kw)):
                if len(w) > 2 and w not in ["the", "for", "and", "scheme"]:
                    tokens.add(w.lower())

        results = []
        scored_schemes = []

        for node_id, data in self.graph.nodes(data=True):
            if data.get("label") == "Scheme":
                s_name = data.get("name", "").lower()
                s_desc = data.get("description", "").lower()

                score = 0
                # Exact or phrase match
                if raw_scheme_name and raw_scheme_name in s_name:
                    score += 15

                # Token overlap scoring
                for t in tokens:
                    if t in s_name:
                        score += 5
                    elif t in s_desc:
                        score += 2

                if score > 0:
                    scored_schemes.append((score, node_id, data))

        # Sort schemes by relevance score
        scored_schemes.sort(key=lambda x: x[0], reverse=True)
        target_schemes = [item[1:] for item in scored_schemes[:1]]

        for s_id, s_data in target_schemes:
            for _, target_id, edge_data in self.graph.out_edges(s_id, data=True):
                target_node = self.graph.nodes.get(target_id, {})
                results.append({
                    "scheme_id": s_id,
                    "scheme_name": s_data.get("name"),
                    "source_url": s_data.get("url"),
                    "description": s_data.get("description"),
                    "relationship": edge_data.get("type", "RELATED_TO"),
                    "target_type": target_node.get("label", "Entity"),
                    "target_name": target_node.get("name", "")
                })

        return results

    def get_summary_stats(self) -> Dict[str, Any]:
        if self.graph.number_of_nodes() == 0:
            self.connect()

        labels = set()
        for _, d in self.graph.nodes(data=True):
            if "label" in d:
                labels.add(d["label"])

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_relationships": self.graph.number_of_edges(),
            "labels": list(labels)
        }