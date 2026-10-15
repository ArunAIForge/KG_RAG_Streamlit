# api/app.py
import asyncio
import logging
from contextlib import asynccontextmanager
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.settings import settings
from graph.neo4j_store import Neo4jGraphStore
from graph.networkx_store import NetworkXGraphStore
from generation.chain import KGRAGChain
from ingestion.tn_scraper import TNAgricultureScraper
from extraction.extractor import SchemeGraphExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Shared database instances
neo4j_store = Neo4jGraphStore()
networkx_store = NetworkXGraphStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up connections
    try:
        networkx_store.connect()
        logger.info("Application startup: NetworkX in-memory store ready.")
    except Exception as e:
        logger.warning(f"NetworkX initialization notice: {e}")

    try:
        neo4j_store.connect()
        logger.info("Application startup: Neo4j AuraDB store ready.")
    except Exception as e:
        logger.warning(f"Neo4j startup connection notice: {e}")

    yield

    # Shutdown
    networkx_store.close()
    neo4j_store.close()
    logger.info("Application shutdown: All graph connections released.")

app = FastAPI(
    title="Tamil Nadu Government Schemes KG-RAG API",
    description="Production-grade Knowledge Graph RAG API for Tamil Nadu Government Schemes with Guardrails and Dual Graph Stores.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GraphBackend(str, Enum):
    NEO4J = "neo4j"
    NETWORKX = "networkx"


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="Citizen inquiry about schemes")
    backend: GraphBackend = Field(default=GraphBackend.NEO4J, description="Graph storage engine to query")


class QueryResponse(BaseModel):
    question: str
    answer: str
    guardrail_status: str
    schemes_matched: List[str]
    source_urls: List[str]
    backend_used: str


class IngestResponse(BaseModel):
    status: str
    message: str
    target_schemes_limit: Optional[int]


def get_rag_chain(backend: GraphBackend) -> KGRAGChain:
    """Factory creating KG-RAG chain targeting selected graph backend."""
    if backend == GraphBackend.NETWORKX:
        return KGRAGChain(store=networkx_store)
    else:
        return KGRAGChain(store=neo4j_store)


@app.get("/health", tags=["Monitoring"])
def health_check(backend: GraphBackend = Query(GraphBackend.NEO4J)):
    """Health probe reporting backend connection status and node counts."""
    try:
        store = networkx_store if backend == GraphBackend.NETWORKX else neo4j_store
        stats = store.get_summary_stats()
        return {
            "status": "healthy",
            "backend": backend.value,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database backend unhealthy: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["Retrieval & Generation"])
def ask_scheme_question(request: QueryRequest):
    """Answers citizen inquiries using Knowledge Graph traversal with 3-tier guardrails."""
    try:
        rag = get_rag_chain(request.backend)
        result = rag.run(request.question)
        
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            guardrail_status=result["guardrail_status"],
            schemes_matched=result["schemes_matched"],
            source_urls=result["source_urls"],
            backend_used=request.backend.value
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


async def background_ingestion_task(limit: Optional[int]):
    """Background task to fetch live schemes, extract triples, and populate both graph stores."""
    logger.info("Starting background ingestion pipeline...")
    scraper = TNAgricultureScraper()
    await scraper.scrape_all(limit=limit)

    extractor = SchemeGraphExtractor()
    kg_data = extractor.process_all(limit=limit)

    # Ingest into Neo4j
    neo4j_store.connect()
    for n in kg_data.nodes:
        neo4j_store.upsert_node(n)
    for r in kg_data.relationships:
        neo4j_store.upsert_relationship(r)

    # Ingest into NetworkX
    networkx_store.connect()
    for n in kg_data.nodes:
        networkx_store.upsert_node(n)
    for r in kg_data.relationships:
        networkx_store.upsert_relationship(r)
    networkx_store.close()

    logger.info("Background ingestion completed successfully for both stores.")


@app.post("/ingest", response_model=IngestResponse, tags=["Data Pipeline"])
def trigger_ingestion(background_tasks: BackgroundTasks, limit: Optional[int] = 5):
    """Triggers background scraping and graph sync from official government portal."""
    background_tasks.add_task(background_ingestion_task, limit)
    return IngestResponse(
        status="accepted",
        message="Scheme ingestion task initiated in background.",
        target_schemes_limit=limit
    )