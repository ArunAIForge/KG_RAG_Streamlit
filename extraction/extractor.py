# extraction/extractor.py
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from rich.console import Console
from rich.table import Table

from config.settings import settings
from extraction.schemas import (
    SchemeKnowledgeGraph,
    NodeEntity,
    RelationshipTriple,
    EntityType,
    RelationType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
console = Console()

# Notice double curly braces {{scheme_id}} so LangChain treats it as literal text
EXTRACTION_SYSTEM_PROMPT = """You are an expert Knowledge Graph architect.
Convert the provided Tamil Nadu government scheme JSON record into a structured Knowledge Graph of entities and relationships.

Strict Node Rules:
- Create a 'Scheme' node with id 'SCHEME_{{scheme_id}}'.
- Create a 'Department' node (e.g. 'DEPT_AGRI').
- Create 'BeneficiaryGroup' nodes for target beneficiaries (e.g., 'BENEFICIARY_FARMERS', 'BENEFICIARY_SC_ST', 'BENEFICIARY_WOMEN_FARMERS').
- Create 'Benefit' nodes for subsidies, grants, assistance, or machinery.
- Create 'EligibilityCriteria' nodes for conditions, documents, landholding rules, or district requirements.
- Create 'ApplicationStep' nodes for where to apply or whom to contact.

Strict Relationship Rules:
- (:Scheme)-[:ADMINISTERED_BY]->(:Department)
- (:Scheme)-[:TARGETS_BENEFICIARY]->(:BeneficiaryGroup)
- (:Scheme)-[:PROVIDES_BENEFIT]->(:Benefit)
- (:Scheme)-[:REQUIRES_ELIGIBILITY]->(:EligibilityCriteria)
- (:Scheme)-[:FOLLOWS_PROCEDURE]->(:ApplicationStep)

Ensure every node has a unique, deterministic ID, a human-readable name, and a valid label.
Ensure every relationship points from an existing source node ID to an existing target node ID.
"""


class SchemeGraphExtractor:
    def __init__(self, raw_data_path: Path = settings.DATA_DIR / "tn_agriculture_schemes.json"):
        self.raw_data_path = raw_data_path
        self.output_graph_path = settings.DATA_DIR / "knowledge_graph_extracted.json"

        api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing! Set it in your .env file.")

        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=0.0,
            api_key=api_key
        )
        self.structured_llm = self.llm.with_structured_output(
            SchemeKnowledgeGraph, 
            method="function_calling"
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("human", "Scheme data:\n{scheme_json}")
        ])

        self.chain = self.prompt | self.structured_llm

    def extract_from_record(self, scheme_record: Dict[str, Any]) -> SchemeKnowledgeGraph:
        """Invokes structured LLM extraction for a single scheme record."""
        payload_str = json.dumps(scheme_record, indent=2, ensure_ascii=False)
        return self.chain.invoke({"scheme_json": payload_str})

    def process_all(self, limit: int = None) -> SchemeKnowledgeGraph:
        if not self.raw_data_path.exists():
            raise FileNotFoundError(f"Missing scraped data at {self.raw_data_path}. Run Step 2 first.")

        with open(self.raw_data_path, "r", encoding="utf-8") as f:
            schemes: List[Dict[str, Any]] = json.load(f)

        target = schemes[:limit] if limit else schemes
        console.print(f"[bold cyan]Extracting Knowledge Graph for {len(target)} schemes...[/bold cyan]")

        unified_graph = SchemeKnowledgeGraph()
        seen_node_ids = set()

        for idx, scheme in enumerate(target, start=1):
            title = scheme.get("title", f"Scheme #{idx}")
            console.print(f"[{idx}/{len(target)}] Processing: [yellow]{title}[/yellow]")
            try:
                sub_graph = self.extract_from_record(scheme)
                console.print(f"    Extracted [green]{len(sub_graph.nodes)}[/green] nodes, [yellow]{len(sub_graph.relationships)}[/yellow] relationships")

                for node in sub_graph.nodes:
                    if node.id not in seen_node_ids:
                        seen_node_ids.add(node.id)
                        unified_graph.nodes.append(node)

                for rel in sub_graph.relationships:
                    unified_graph.relationships.append(rel)

            except Exception as e:
                console.print(f"    [red]Extraction failed for '{title}': {e}[/red]")

        # Persist extracted graph
        with open(self.output_graph_path, "w", encoding="utf-8") as f:
            json.dump(unified_graph.model_dump(), f, indent=2, ensure_ascii=False)

        console.print(f"\n[bold green]✔ Extraction complete![/bold green] Total unique nodes: [cyan]{len(unified_graph.nodes)}[/cyan], total relationships: [yellow]{len(unified_graph.relationships)}[/yellow]")
        return unified_graph


def display_graph_summary(graph: SchemeKnowledgeGraph):
    console.print("\n[bold cyan]=== Knowledge Graph Extraction Summary ===[/bold cyan]\n")

    node_table = Table(title=f"Extracted Nodes ({len(graph.nodes)} Total)", show_lines=True)
    node_table.add_column("Node ID", style="cyan", width=32)
    node_table.add_column("Label / Type", style="magenta", width=20)
    node_table.add_column("Entity Name", style="green", width=38)

    for node in graph.nodes[:12]:
        lbl = node.label.value if hasattr(node.label, "value") else str(node.label)
        node_table.add_row(node.id, lbl, node.name[:36])

    console.print(node_table)

    rel_table = Table(title=f"Extracted Relationships ({len(graph.relationships)} Total)", show_lines=True)
    rel_table.add_column("Source Node ID", style="cyan", width=28)
    rel_table.add_column("Edge Type", style="yellow", width=24)
    rel_table.add_column("Target Node ID", style="magenta", width=28)

    for rel in graph.relationships[:12]:
        rtype = rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type)
        rel_table.add_row(rel.source_id, rtype, rel.target_id)

    console.print(rel_table)


if __name__ == "__main__":
    extractor = SchemeGraphExtractor()
    kg = extractor.process_all()
    display_graph_summary(kg)