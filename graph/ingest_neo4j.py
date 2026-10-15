# graph/ingest_neo4j.py
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import settings
from extraction.schemas import SchemeKnowledgeGraph, NodeEntity, RelationshipTriple
from graph.neo4j_store import Neo4jGraphStore

console = Console()


def run_neo4j_ingestion():
    graph_file = settings.DATA_DIR / "knowledge_graph_extracted.json"
    if not graph_file.exists():
        console.print(f"[bold red]File not found: {graph_file}. Make sure Step 3 completed successfully.[/bold red]")
        return

    with open(graph_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Deserialize into Pydantic models
    kg_data = SchemeKnowledgeGraph(**raw_data)

    console.print(Panel(
        f"Nodes to Ingest: [cyan]{len(kg_data.nodes)}[/cyan]\n"
        f"Relationships to Ingest: [cyan]{len(kg_data.relationships)}[/cyan]",
        title="[bold green]Starting Neo4j Ingestion[/bold green]"
    ))

    store = Neo4jGraphStore()
    try:
        store.connect()

        # Ingest Nodes
        with console.status("[bold green]Ingesting Nodes into Neo4j AuraDB...") as status:
            for idx, node in enumerate(kg_data.nodes, start=1):
                store.upsert_node(node)
            console.print(f"✔ Successfully upserted [bold green]{len(kg_data.nodes)}[/bold green] nodes.")

        # Ingest Relationships
        with console.status("[bold yellow]Ingesting Relationships into Neo4j AuraDB...") as status:
            for idx, rel in enumerate(kg_data.relationships, start=1):
                store.upsert_relationship(rel)
            console.print(f"✔ Successfully upserted [bold yellow]{len(kg_data.relationships)}[/bold yellow] relationships.")

        # Validate by querying back from Neo4j
        stats = store.get_summary_stats()

        stats_table = Table(title="[bold cyan]Neo4j AuraDB Live Database Stats[/bold cyan]", show_lines=True)
        stats_table.add_column("Metric", style="white", width=25)
        stats_table.add_column("Value in AuraDB", style="green", width=35)

        stats_table.add_row("Total Graph Nodes", str(stats["total_nodes"]))
        stats_table.add_row("Total Graph Relationships", str(stats["total_relationships"]))
        stats_table.add_row("Active Labels", ", ".join(stats["labels"]))

        console.print(stats_table)

        # Sample Cypher verification query: Schemes and their Target Beneficiaries
        sample_query = """
        MATCH (s:Scheme)-[:TARGETS_BENEFICIARY]->(b:BeneficiaryGroup)
        RETURN s.name AS Scheme, b.name AS Beneficiary
        LIMIT 5
        """
        sample_results = store.query(sample_query)

        query_table = Table(title="[bold magenta]Live Traversal Test: Schemes ➔ Beneficiaries[/bold magenta]", show_lines=True)
        query_table.add_column("Scheme", style="bold white", width=35)
        query_table.add_column("Target Beneficiary", style="yellow", width=30)

        for row in sample_results:
            query_table.add_row(row["Scheme"][:35], row["Beneficiary"][:30])

        console.print(query_table)

    finally:
        store.close()


if __name__ == "__main__":
    run_neo4j_ingestion()