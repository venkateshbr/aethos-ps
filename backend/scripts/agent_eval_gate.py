"""Run the offline agent-eval gate and print a drift report (#407).

Deterministic (no LLM/network). Exits non-zero on any misclassification or an
uncovered golden case, so it can be a CI step or a pre-commit check. The markdown
it prints doubles as the drift dashboard for CI logs / an uploaded artifact.

Usage:
    uv run python -m scripts.agent_eval_gate
    uv run python -m scripts.agent_eval_gate --out eval-drift.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.evals.gate import render_markdown, run_offline_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline agent-eval gate")
    parser.add_argument("--out", help="also write the markdown report to this path")
    args = parser.parse_args()

    report = run_offline_gate()
    markdown = render_markdown(report)
    print(markdown)
    if args.out:
        Path(args.out).write_text(markdown)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
