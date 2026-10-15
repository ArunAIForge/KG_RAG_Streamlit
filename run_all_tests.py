# run_all_tests.py
import sys
import time
from pathlib import Path
import pytest
from rich.console import Console
from rich.panel import Panel

# Ensure project root is first on Python module search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

console = Console()

def main():
    console.print(Panel(
        "[bold cyan]Tamil Nadu Schemes KG-RAG System[/bold cyan]\n"
        "[yellow]Automated Test Suite Execution[/yellow]",
        title="KG-RAG Test Runner",
        border_style="cyan"
    ))

    start_time = time.time()

    pytest_args = [
        str(PROJECT_ROOT / "tests" / "test_api.py"),
        "-v",
        "-s",
        "-rA",
        f"-o", f"pythonpath={PROJECT_ROOT}"
    ]

    exit_code = pytest.main(pytest_args)
    duration = time.time() - start_time

    if exit_code == 0:
        console.print(f"\n[bold green]✔ All test cases passed successfully in {duration:.2f} seconds![/bold green]\n")
    else:
        console.print(f"\n[bold red]✖ Test run finished with exit code: {exit_code} in {duration:.2f} seconds.[/bold red]\n")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()