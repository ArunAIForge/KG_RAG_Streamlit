# graph/neo4j_store.py
import logging
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver

from config.settings import settings
from extraction.schemas import NodeEntity, RelationshipTriple
from graph.base import BaseGraphStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class Neo4jGraphStore(BaseGraphStore):
    def __init__(
        self,
        uri: str = settings.NEO4J_URI,
        username: str = settings.NEO4J_USERNAME,
        password: str = settings.NEO4J_PASSWORD,
    ):
        self.uri = uri.strip()
        self.username = username.strip()
        self.password = password.strip()
        self._driver: Optional[Driver] = None

    def connect(self) -> None:
        if not self._driver:
            target_uri = self.uri
            try:
                self._driver = GraphDatabase.driver(
                    target_uri,
                    auth=(self.username, self.password),
                    max_connection_lifetime=30 * 60,
                    max_connection_pool_size=50,
                )
                self._driver.verify_connectivity()
                logger.info("Successfully connected to Neo4j AuraDB.")
            except Exception as first_err:
                logger.warning(f"Standard connection failed: {first_err}. Attempting fallback URI...")
                if target_uri.startswith("neo4j+s://"):
                    fallback_uri = target_uri.replace("neo4j+s://", "neo4j+ssc://", 1)
                elif target_uri.startswith("bolt+s://"):
                    fallback_uri = target_uri.replace("bolt+s://", "bolt+ssc://", 1)
                else:
                    fallback_uri = target_uri

                self._driver = GraphDatabase.driver(
                    fallback_uri,
                    auth=(self.username, self.password),
                    max_connection_lifetime=30 * 60,
                    max_connection_pool_size=50,
                )
                self._driver.verify_connectivity()
                logger.info("Connected to Neo4j AuraDB via fallback protocol.")

            self._init_constraints()

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver connection closed.")

    def _init_constraints(self) -> None:
        """Create uniqueness constraints on node IDs."""
        labels = [
            "Scheme",
            "Department",
            "Organisation",
            "BeneficiaryGroup",
            "Benefit",
            "EligibilityCriteria",
            "ApplicationStep",
            "Sponsor",
        ]
        with self._driver.session() as session:
            for label in labels:
                query = f"""
                CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label})
                REQUIRE n.id IS UNIQUE
                """
                session.run(query)
        logger.info("Neo4j schema constraints verified.")

    def upsert_node(self, node: NodeEntity) -> None:
        """Idempotent node creation using dynamic label and MERGE on unique ID."""
        if not self._driver:
            self.connect()

        label = node.label.value if hasattr(node.label, "value") else str(node.label)
        cypher = f"""
        MERGE (n:{label} {{id: $id}})
        SET n.name = $name,
            n += $properties
        """
        params = {
            "id": node.id,
            "name": node.name,
            "properties": node.properties or {}
        }
        with self._driver.session() as session:
            session.run(cypher, params)

    def upsert_relationship(self, rel: RelationshipTriple) -> None:
        """Idempotent relationship creation connecting source and target nodes."""
        if not self._driver:
            self.connect()

        rel_type = rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type)
        cypher = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r += $properties
        """
        params = {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "properties": rel.properties or {}
        }
        with self._driver.session() as session:
            session.run(cypher, params)

    def query(self, query_str: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a Cypher query and returns dictionary rows."""
        if not self._driver:
            self.connect()
        params = params or {}
        with self._driver.session() as session:
            result = session.run(query_str, params)
            return [record.data() for record in result]

    def get_summary_stats(self) -> Dict[str, Any]:
        """Inspects total node and relationship counts."""
        if not self._driver:
            self.connect()

        node_count_q = "MATCH (n) RETURN count(n) AS node_count"
        rel_count_q = "MATCH ()-[r]->() RETURN count(r) AS rel_count"
        labels_q = "CALL db.labels() YIELD label RETURN collect(label) AS labels"

        with self._driver.session() as session:
            node_count = session.run(node_count_q).single()["node_count"]
            rel_count = session.run(rel_count_q).single()["rel_count"]
            labels = session.run(labels_q).single()["labels"]

        return {
            "total_nodes": node_count,
            "total_relationships": rel_count,
            "labels": labels
        }