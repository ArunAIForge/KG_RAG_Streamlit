# evaluation/evaluate_rag.py
import json
import logging
import os
from typing import List

from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric
)
from deepeval.test_case import LLMTestCase
from rich.console import Console
from rich.table import Table

from config.settings import settings
from generation.chain import KGRAGChain

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
console = Console()


# Gold-standard evaluation dataset for TN Agriculture Schemes
EVAL_DATASET = [
    {
        "input": "What are the eligibility criteria for the Training to Farmers scheme?",
        "expected_output": "All maize growing farmers in specified districts such as Coimbatore, Dindigul, and Salem are eligible, with priority given to small/marginal farmers, 24% flow to SC/ST farmers, and 20% flow to women farmers."
    },
    {
        "input": "What benefits are provided under the Distribution of Rhizobium Packets scheme?",
        "expected_output": "The scheme provides subsidies for Rhizobium packets to farmers producing Foundation and Certified class seeds."
    },
    {
        "input": "Who can apply for the Distribution of Nuclear Poly Hedrosis Virus scheme and where should applications be submitted?",
        "expected_output": "Farmers raising seed farms with pulses crop can apply. Applications are submitted to Assistant Agricultural Officers at the village level, Deputy Agricultural Officers at block level, or the Joint Director of Agriculture at district level."
    }
]


def run_evaluation():
    console.print("\n[bold cyan]=== Initializing DeepEval KG-RAG Test Suite ===[/bold cyan]\n")
    
    # Initialize the KG-RAG pipeline
    rag = KGRAGChain()

    # Define Metrics with thresholds
    # DeepEval will use the OPENAI_API_KEY from environment/settings as the evaluation judge
    relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model="gpt-4o-mini")
    faithfulness_metric = FaithfulnessMetric(threshold=0.7, model="gpt-4o-mini")
    contextual_relevancy_metric = ContextualRelevancyMetric(threshold=0.6, model="gpt-4o-mini")

    test_cases: List[LLMTestCase] = []
    runs_summary = []

    for idx, item in enumerate(EVAL_DATASET, start=1):
        q = item["input"]
        expected = item["expected_output"]
        console.print(f"[{idx}/{len(EVAL_DATASET)}] Executing KG-RAG for: [yellow]'{q}'[/yellow]")

        rag_output = rag.run(q)
        actual_answer = rag_output["answer"]
        context_str = rag_output.get("retrieved_context", "")

        # Format retrieved context into string list expected by DeepEval
        retrieval_context = [c.strip() for c in context_str.split("====================") if c.strip()]
        if not retrieval_context:
            retrieval_context = ["No graph context found."]

        # Construct DeepEval Test Case
        case = LLMTestCase(
            input=q,
            actual_output=actual_answer,
            expected_output=expected,
            retrieval_context=retrieval_context
        )
        test_cases.append(case)

        # Measure individual metrics
        relevancy_metric.measure(case)
        faithfulness_metric.measure(case)
        contextual_relevancy_metric.measure(case)

        runs_summary.append({
            "question": q,
            "relevancy": relevancy_metric.score,
            "faithfulness": faithfulness_metric.score,
            "context_relevancy": contextual_relevancy_metric.score,
            "passed": relevancy_metric.is_successful() and faithfulness_metric.is_successful() and contextual_relevancy_metric.is_successful()
        })

    # Render results table
    table = Table(title="[bold green]DeepEval KG-RAG Quantitative Scorecard[/bold green]", show_lines=True)
    table.add_column("Query Evaluated", style="white", width=36)
    table.add_column("Answer Relevancy", style="cyan", justify="center", width=18)
    table.add_column("Faithfulness", style="magenta", justify="center", width=16)
    table.add_column("Context Relevancy", style="yellow", justify="center", width=18)
    table.add_column("Verdict", style="bold", justify="center", width=12)

    for r in runs_summary:
        verdict = "[green]PASSED[/green]" if r["passed"] else "[red]FAILED[/red]"
        table.add_row(
            r["question"],
            f"{r['relevancy']:.2f} (min 0.70)",
            f"{r['faithfulness']:.2f} (min 0.70)",
            f"{r['context_relevancy']:.2f} (min 0.60)",
            verdict
        )

    console.print("\n")
    console.print(table)
    console.print("\n[bold green]✔ Evaluation Run Completed![/bold green]")


if __name__ == "__main__":
    run_evaluation()