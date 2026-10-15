# test_query.py
from rich.console import Console
from rich.panel import Panel
from generation.chain import KGRAGChain

console = Console()

def run_test():
    rag = KGRAGChain()
    
    test_queries = [
        "What financial assistance or training is provided to farmers, and who is eligible?",
        "How can I get Rhizobium packets and what are their benefits?",
        "Can I get a loan to buy a commercial airplane from the agriculture department?"  # Out-of-scope test
    ]

    for q in test_queries:
        console.print(f"\n[bold cyan]User Query:[/bold cyan] [yellow]{q}[/yellow]")
        result = rag.run(q)
        
        console.print(Panel(
            result["answer"],
            title=f"[bold green]KG-RAG Response (Schemes Matched: {len(result['schemes_matched'])})[/bold green]",
            border_style="green"
        ))
        
        if result["source_urls"]:
            console.print(f"[dim]Source Citations: {result['source_urls']}[/dim]")

if __name__ == "__main__":
    run_test()