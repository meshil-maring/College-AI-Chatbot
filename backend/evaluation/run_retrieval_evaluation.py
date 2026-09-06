"""Run the Phase 3.10 retrieval evaluator against Supabase and OpenRouter."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.evaluator import evaluate_dataset, load_dataset, write_report

DEFAULT_DATASET = Path(__file__).with_name("retrieval_dataset.jsonl")
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "retrieval_evaluation.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    cases = load_dataset(args.dataset)
    report = evaluate_dataset(cases)
    report["metadata"]["dataset_path"] = str(args.dataset.resolve())
    write_report(report, args.output)
    print(f"Evaluated {len(cases)} cases; report written to {args.output}")


if __name__ == "__main__":
    main()
