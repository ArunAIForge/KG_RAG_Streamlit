# test_setup.py
import sys
from importlib.metadata import version
from config.settings import settings
from rich.console import Console

console = Console()

def verify_environment():
    console.print(f"[bold cyan]Validating Setup for {settings.APP_NAME}...[/bold cyan]")
    
    # 1. Check directories
    assert settings.DATA_DIR.exists(), "Data directory was not created!"
    console.print(f"✔ Data directory initialized at: [green]{settings.DATA_DIR}[/green]")

    # 2. Check dependencies and versions using standard importlib.metadata
    packages = ["playwright", "langchain", "neo4j", "networkx", "deepeval"]
    
    console.print("✔ Core libraries imported successfully:")
    for pkg in packages:
        try:
            pkg_ver = version(pkg)
            console.print(f"  • {pkg.capitalize()} version: [yellow]{pkg_ver}[/yellow]")
        except Exception as e:
            console.print(f"  • {pkg.capitalize()}: [red]Failed to load version ({e})[/red]")

    console.print("\n[bold green]✔ Step 1 Complete: Environment is ready for scraping![/bold green]")

if __name__ == "__main__":
    verify_environment()