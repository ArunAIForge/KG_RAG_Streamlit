# debug_extraction.py
import json
import os
import traceback
from pathlib import Path
from config.settings import settings
from extraction.schemas import SchemeKnowledgeGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from rich.console import Console

console = Console()

def debug():
    console.print("\n[bold cyan]=== Step 3 Extraction Diagnostic ===[/bold cyan]")
    
    # 1. Check API Key
    api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        console.print("[bold red]❌ CRITICAL: OPENAI_API_KEY is empty in .env and environment variables![/bold red]")
        return
    else:
        masked_key = api_key[:7] + "..." + api_key[-4:]
        console.print(f"✔ API Key detected: [green]{masked_key}[/green]")

    # 2. Check Scraped File
    scraped_file = settings.DATA_DIR / "tn_agriculture_schemes.json"
    if not scraped_file.exists():
        console.print(f"[bold red]❌ Scraped data missing at: {scraped_file}[/bold red]")
        return
    
    with open(scraped_file, "r", encoding="utf-8") as f:
        schemes = json.load(f)
    console.print(f"✔ Scraped schemes loaded: [green]{len(schemes)} schemes found[/green]")

    first_scheme = schemes[0]
    console.print(f"\n[yellow]Testing extraction on Scheme #1:[/yellow] '{first_scheme.get('title')}'")

    # 3. Test LLM Connection & Structured Extraction
    try:
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=0.0,
            api_key=api_key
        )
        
        # Test basic ping first
        console.print("Pinging OpenAI model...")
        ping = llm.invoke("respond with 'pong'")
        console.print(f"✔ LLM Ping Response: [green]{ping.content}[/green]")

        console.print("Running structured schema extraction...")
        structured_llm = llm.with_structured_output(SchemeKnowledgeGraph, method="function_calling")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract all schemes, departments, beneficiaries, benefits, and steps into the schema."),
            ("human", "Scheme data:\n{scheme_json}")
        ])
        
        chain = prompt | structured_llm
        result: SchemeKnowledgeGraph = chain.invoke({
            "scheme_json": json.dumps(first_scheme, ensure_ascii=False)
        })

        console.print(f"\n[bold green]✔ Extraction Succeeded![/bold green]")
        console.print(f"Nodes found: [cyan]{len(result.nodes)}[/cyan]")
        console.print(f"Relationships found: [cyan]{len(result.relationships)}[/cyan]")
        if result.nodes:
            console.print(f"Sample node: [magenta]{result.nodes[0]}[/magenta]")

    except Exception as e:
        console.print(f"\n[bold red]❌ Extraction Call Failed:[/bold red]")
        traceback.print_exc()

if __name__ == "__main__":
    debug()