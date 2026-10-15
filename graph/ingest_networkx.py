# graph/ingest_networkx.py
import json
from rich.console import Console
from rich.table import Table

from config.settings import settings
from extraction.schemas import SchemeKnowledgeGraph
from graph.networkx_store import NetworkXGraphStore

console = Console()

def run_networkx_ingestion():
    graph_file = settings.DATA_DIR / "knowledge_graph_extracted.json"
    with open(graph_file, "r", encoding="utf-8") as f:
        kg_data = SchemeKnowledgeGraph(**json.load(f))

    nx_store = NetworkXGraphStore()
    nx_store.connect()

    for node in kg_data.nodes:
        nx_store.upsert_node(node)

    for rel in kg_data.relationships:
        nx_store.upsert_relationship(rel)

    nx_store.close()

    stats = nx_store.get_summary_stats()
    
    table = Table(title="[bold green]NetworkX In-Memory Store Stats[/bold green]", show_lines=True)
    table.add_column("Metric", style="white")
    table.add_column("Value", style="green")
    table.add_row("Nodes Ingested", str(stats["total_nodes"]))
    table.add_row("Edges Ingested", str(stats["total_relationships"]))
    table.add_row("Node Labels", ", ".join(stats["labels"]))
    console.print(table)

if __name__ == "__main__":
    run_networkx_ingestion()