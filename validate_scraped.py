# validate_scraped.py
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
data_file = Path("data/raw/tn_agriculture_schemes.json")

def inspect_scraped_data():
    if not data_file.exists():
        console.print(f"[bold red]File not found: {data_file}[/bold red]")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    console.print(f"\n[bold cyan]Found {len(schemes)} scraped schemes in {data_file}[/bold cyan]\n")

    for idx, scheme in enumerate(schemes, start=1):
        raw_fields = scheme.get("all_raw_fields", {})
        has_real_fields = len(raw_fields) > 0

        # Status check
        status = "[bold green]✔ DETAILED DATA CAPTURED[/bold green]" if has_real_fields else "[bold red]⚠ NO RAW FIELDS FOUND[/bold red]"

        console.print(Panel(
            f"[bold yellow]Scheme Name:[/bold yellow] {scheme.get('title')}\n"
            f"[bold yellow]URL:[/bold yellow] {scheme.get('url')}\n"
            f"[bold yellow]Beneficiary:[/bold yellow] {scheme.get('beneficiary')}\n"
            f"[bold yellow]Eligibility:[/bold yellow] {scheme.get('eligibility')}\n"
            f"[bold yellow]Benefits:[/bold yellow] {scheme.get('benefits')}\n"
            f"[bold yellow]How to Apply:[/bold yellow] {scheme.get('how_to_apply')}\n"
            f"[bold yellow]Whom to Contact:[/bold yellow] {scheme.get('whom_to_contact')}\n"
            f"[bold yellow]Raw Table Keys Found ({len(raw_fields)}):[/bold yellow] {list(raw_fields.keys())}",
            title=f"Scheme #{idx} — {status}",
            border_style="green" if has_real_fields else "red"
        ))

if __name__ == "__main__":
    inspect_scraped_data()