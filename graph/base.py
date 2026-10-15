# graph/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from extraction.schemas import NodeEntity, RelationshipTriple


class BaseGraphStore(ABC):
    """Abstract interface for Graph Storage implementations (Neo4j, NetworkX, etc.)."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the graph database."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection cleanly."""
        pass

    @abstractmethod
    def upsert_node(self, node: NodeEntity) -> None:
        """Insert or update a node idempotently."""
        pass

    @abstractmethod
    def upsert_relationship(self, rel: RelationshipTriple) -> None:
        """Insert or update a relationship idempotently."""
        pass

    @abstractmethod
    def query(self, query_str: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a graph query and return rows of records."""
        pass

    @abstractmethod
    def get_summary_stats(self) -> Dict[str, Any]:
        """Return counts of nodes, labels, and relationships."""
        pass