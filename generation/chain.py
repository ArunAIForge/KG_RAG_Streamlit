# generation/chain.py
import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config.settings import settings
from graph.neo4j_store import Neo4jGraphStore
from retrieval.graph_retriever import KGRetriever
from guardrails.validator import InputGuardrail, RetrievalGuardrail, OutputGuardrail

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are an official Tamil Nadu Government Schemes Knowledge Assistant.
Your objective is to answer citizen queries accurately, objectively, and completely based ONLY on the retrieved Knowledge Graph facts below.

Strict Directives:
1. Use ONLY the provided Graph Facts and Scheme Details.
2. If the retrieved context does not contain enough evidence to answer the question, state:
   "The available government scheme records do not contain sufficient information to answer this question."
   Do NOT attempt to guess or hallucinate eligibility, subsidies, or procedures not documented in the context.
3. Always cite the exact Scheme Name and the official source URL provided in the context.
4. Highlight eligibility criteria, beneficiary groups, and application procedures in clear bullet points.
"""

class KGRAGChain:
    def __init__(self, store: Optional[Neo4jGraphStore] = None):
        self.store = store or Neo4jGraphStore()
        self.retriever = KGRetriever(store=self.store)
        
        # Guardrail instances
        self.input_guard = InputGuardrail()
        self.retrieval_guard = RetrievalGuardrail()
        self.output_guard = OutputGuardrail()

        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", RAG_SYSTEM_PROMPT),
            ("human", "User Question: {question}\n\nRetrieved Knowledge Graph Context:\n{context}\n\nHelpful, Grounded Answer:")
        ])
        
        self.chain = self.prompt | self.llm | StrOutputParser()

    def run(self, question: str) -> Dict[str, Any]:
        """
        Executes full KG-RAG flow with multi-layer Guardrails:
        Input Guard -> KG Retrieval -> Retrieval Guard -> Answer Synthesis -> Output Guard
        """
        # --- Layer 1: Input Guardrail ---
        input_check = self.input_guard.validate(question)
        if not input_check.is_safe:
            logger.warning(f"Blocked by Input Guardrail: {input_check.reason}")
            return {
                "question": question,
                "answer": f"Request could not be processed: {input_check.reason}",
                "guardrail_status": "BLOCKED_INPUT",
                "retrieved_context": "",
                "schemes_matched": [],
                "source_urls": []
            }

        # --- Subgraph Retrieval ---
        retrieval_data = self.retriever.retrieve_subgraph(question)

        # --- Layer 2: Retrieval Guardrail ---
        retrieval_check = self.retrieval_guard.validate(retrieval_data)
        if not retrieval_check.is_safe:
            logger.info(f"Retrieval Guardrail notice: {retrieval_check.reason}")
            # Safe fallback for out-of-scope or empty results
            return {
                "question": question,
                "answer": "The available government scheme records do not contain sufficient information to answer this question.",
                "guardrail_status": "BLOCKED_RETRIEVAL",
                "retrieved_context": "",
                "schemes_matched": [],
                "source_urls": []
            }

        formatted_context = self.retriever.format_context_for_prompt(retrieval_data)

        # --- Generation ---
        candidate_answer = self.chain.invoke({
            "question": question,
            "context": formatted_context
        })

        # --- Layer 3: Output Guardrail ---
        output_check = self.output_guard.validate(formatted_context, candidate_answer)
        if not output_check.is_safe:
            logger.warning(f"Output Guardrail flagged hallucination: {output_check.reason}")
            final_answer = "The available government scheme records do not contain sufficient verified information to reliably answer this question."
            status = "BLOCKED_OUTPUT_HALLUCINATION"
        else:
            final_answer = candidate_answer
            status = "PASSED_ALL_GUARDRAILS"

        return {
            "question": question,
            "answer": final_answer,
            "guardrail_status": status,
            "retrieved_context": formatted_context,
            "schemes_matched": [s["name"] for s in retrieval_data.get("schemes", [])],
            "source_urls": list({s["url"] for s in retrieval_data.get("schemes", []) if s.get("url")})
        }