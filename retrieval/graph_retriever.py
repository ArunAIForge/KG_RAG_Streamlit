# retrieval/graph_retriever.py
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config.settings import settings
from graph.neo4j_store import Neo4jGraphStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ExtractedQueryEntities(BaseModel):
    keywords: List[str] = Field(description="Key nouns or terms (e.g. ['training', 'seeds', 'rhizobium'])")
    scheme_name: Optional[str] = Field(default=None, description="Exact or closest scheme title mentioned in the user query")


class KGRetriever:
    def __init__(self, store: Optional[Neo4jGraphStore] = None):
        self.store = store or Neo4jGraphStore()
        
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY
        )
        self.entity_extractor = self.llm.with_structured_output(
            ExtractedQueryEntities, 
            method="function_calling"
        )
        
        self.extract_prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract the specific scheme title candidate and primary search keywords from the user question."),
            ("human", "{question}")
        ])
        self.extract_chain = self.extract_prompt | self.entity_extractor

    def extract_search_terms(self, question: str) -> ExtractedQueryEntities:
        return self.extract_chain.invoke({"question": question})

    def retrieve_subgraph(self, question: str) -> Dict[str, Any]:
        """
        Retrieves the exact target scheme subgraph to maximize precision and contextual relevancy.
        """
        terms = self.extract_search_terms(question)
        logger.info(f"Extracted scheme: '{terms.scheme_name}', keywords: {terms.keywords}")

        # Targeted Cypher query: prioritize scheme name match, then fall back to high-confidence keyword match
        cypher = """
        MATCH (s:Scheme)
        WHERE ($scheme_name IS NOT NULL AND toLower(s.name) CONTAINS toLower($scheme_name))
           OR (size($keywords) > 0 AND any(kw IN $keywords WHERE toLower(s.name) CONTAINS toLower(kw)))
        WITH s LIMIT 1
        OPTIONAL MATCH (s)-[r]->(target)
        RETURN 
            s.id AS scheme_id,
            s.name AS scheme_name,
            s.url AS source_url,
            s.description AS description,
            type(r) AS relationship,
            labels(target)[0] AS target_type,
            target.name AS target_name
        """
        
        raw_results = self.store.query(cypher, {
            "scheme_name": terms.scheme_name or "",
            "keywords": terms.keywords
        })

        # Fallback if no specific title matched
        if not raw_results and terms.keywords:
            fallback_cypher = """
            MATCH (s:Scheme)
            WHERE any(kw IN $keywords WHERE toLower(s.description) CONTAINS toLower(kw))
            WITH s LIMIT 1
            OPTIONAL MATCH (s)-[r]->(target)
            RETURN 
                s.id AS scheme_id,
                s.name AS scheme_name,
                s.url AS source_url,
                s.description AS description,
                type(r) AS relationship,
                labels(target)[0] AS target_type,
                target.name AS target_name
            """
            raw_results = self.store.query(fallback_cypher, {"keywords": terms.keywords})

        # Assemble retrieved records
        schemes_context: Dict[str, Dict[str, Any]] = {}
        for row in raw_results:
            sid = row.get("scheme_id")
            if not sid:
                continue
            if sid not in schemes_context:
                schemes_context[sid] = {
                    "name": row.get("scheme_name"),
                    "url": row.get("source_url"),
                    "description": row.get("description"),
                    "connected_facts": []
                }
            if row.get("relationship") and row.get("target_name"):
                fact = f"- [{row['relationship']}] ➔ ({row['target_type']}: {row['target_name']})"
                if fact not in schemes_context[sid]["connected_facts"]:
                    schemes_context[sid]["connected_facts"].append(fact)

        return {
            "query_terms": terms.keywords,
            "matched_schemes_count": len(schemes_context),
            "schemes": list(schemes_context.values())
        }

    def format_context_for_prompt(self, retrieval_output: Dict[str, Any]) -> str:
        schemes = retrieval_output.get("schemes", [])
        if not schemes:
            return "No matching schemes or graph relationships found in the database."

        formatted_blocks = []
        for s in schemes:
            block = (
                f"SCHEME: {s['name']}\n"
                f"SOURCE URL: {s.get('url', 'N/A')}\n"
                f"DETAILS: {s.get('description', 'N/A')}\n"
                f"GRAPH RELATIONSHIPS:\n" + "\n".join(s["connected_facts"])
            )
            formatted_blocks.append(block)

        return "\n\n====================\n\n".join(formatted_blocks)