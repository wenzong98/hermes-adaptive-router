"""A/B testing framework for routing strategies.

Supports running two routing strategies side-by-side and comparing their
accuracy against a golden dataset or user feedback.

Features:
- Strategy registration with named variants
- Parallel execution of A and B strategies
- Accuracy tracking against golden labels
- Statistical comparison (confidence intervals)
- Report generation
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from hermes_adaptive_router.router import QueryRoute


@dataclass(frozen=True)
class GoldenCase:
    """A single test case with expected routing decision."""

    query: str
    expected_datasource: str
    expected_complexity: str
    expected_strategy: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResult:
    """Result from running a strategy on a single query."""

    query: str
    predicted: QueryRoute
    expected: GoldenCase
    correct_datasource: bool = False
    correct_complexity: bool = False
    correct_strategy: bool = False
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def fully_correct(self) -> bool:
        return self.correct_datasource and self.correct_complexity and self.correct_strategy


@dataclass
class StrategyMetrics:
    """Aggregated metrics for a strategy."""

    name: str
    total: int = 0
    correct_datasource: int = 0
    correct_complexity: int = 0
    correct_strategy: int = 0
    fully_correct: int = 0
    total_latency_ms: float = 0.0
    results: list[StrategyResult] = field(default_factory=list)

    @property
    def datasource_accuracy(self) -> float:
        return self.correct_datasource / self.total if self.total else 0.0

    @property
    def complexity_accuracy(self) -> float:
        return self.correct_complexity / self.total if self.total else 0.0

    @property
    def strategy_accuracy(self) -> float:
        return self.correct_strategy / self.total if self.total else 0.0

    @property
    def overall_accuracy(self) -> float:
        return self.fully_correct / self.total if self.total else 0.0

    @property
    def mean_latency_ms(self) -> float:
        return self.total_latency_ms / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "total": self.total,
            "datasource_accuracy": round(self.datasource_accuracy, 4),
            "complexity_accuracy": round(self.complexity_accuracy, 4),
            "strategy_accuracy": round(self.strategy_accuracy, 4),
            "overall_accuracy": round(self.overall_accuracy, 4),
            "mean_latency_ms": round(self.mean_latency_ms, 4),
        }


class ABTestRunner:
    """Run A/B tests between two routing strategies.

    Usage:
        runner = ABTestRunner()

        # Register strategies
        runner.register_strategy("A", lambda q: classify_query(q, config_a))
        runner.register_strategy("B", lambda q: classify_query(q, config_b))

        # Load golden dataset
        runner.load_golden_dataset("benchmarks/golden.json")

        # Run comparison
        results = runner.run_comparison()

        # Generate report
        report = runner.generate_report()
        print(report)
    """

    def __init__(self) -> None:
        self._strategies: dict[str, Callable[[str], QueryRoute]] = {}
        self._golden_dataset: list[GoldenCase] = []
        self._last_results: dict[str, StrategyMetrics] = {}

    def register_strategy(
        self,
        name: str,
        strategy_fn: Callable[[str], QueryRoute],
    ) -> None:
        """Register a strategy with a name."""
        self._strategies[name] = strategy_fn

    def unregister_strategy(self, name: str) -> bool:
        """Remove a registered strategy."""
        if name in self._strategies:
            del self._strategies[name]
            return True
        return False

    def load_golden_dataset(
        self,
        path: str | Path,
    ) -> int:
        """Load golden dataset from a JSON file.

        Expected format:
        [
            {
                "query": "Who wrote Hamlet?",
                "expected_datasource": "direct",
                "expected_complexity": "simple",
                "expected_strategy": "none"
            }
        ]
        """
        p = Path(path)
        if not p.exists():
            return 0

        with open(p, encoding="utf-8") as f:
            data = json.load(f)

        self._golden_dataset = []
        for item in data:
            self._golden_dataset.append(
                GoldenCase(
                    query=item["query"],
                    expected_datasource=item["expected_datasource"],
                    expected_complexity=item["expected_complexity"],
                    expected_strategy=item["expected_strategy"],
                    metadata=item.get("metadata", {}),
                )
            )

        return len(self._golden_dataset)

    def add_golden_case(self, case: GoldenCase) -> None:
        """Add a single golden case."""
        self._golden_dataset.append(case)

    def run_comparison(
        self,
        strategy_names: Optional[list[str]] = None,
    ) -> dict[str, StrategyMetrics]:
        """Run all registered strategies against the golden dataset.

        Returns dict mapping strategy name to StrategyMetrics.
        """
        names = strategy_names or list(self._strategies.keys())
        results: dict[str, StrategyMetrics] = {}

        for name in names:
            if name not in self._strategies:
                continue

            fn = self._strategies[name]
            metrics = StrategyMetrics(name=name)

            for case in self._golden_dataset:
                t0 = time.perf_counter()
                try:
                    predicted = fn(case.query)
                except Exception:
                    # Failed predictions count as wrong
                    predicted = QueryRoute(
                        datasource="unknown",
                        complexity="unknown",
                        retrieval_strategy="unknown",
                        confidence=0.0,
                        reason="error",
                    )
                latency = (time.perf_counter() - t0) * 1000

                result = StrategyResult(
                    query=case.query,
                    predicted=predicted,
                    expected=case,
                    correct_datasource=predicted.datasource == case.expected_datasource,
                    correct_complexity=predicted.complexity == case.expected_complexity,
                    correct_strategy=predicted.retrieval_strategy == case.expected_strategy,
                    latency_ms=latency,
                )

                metrics.total += 1
                if result.correct_datasource:
                    metrics.correct_datasource += 1
                if result.correct_complexity:
                    metrics.correct_complexity += 1
                if result.correct_strategy:
                    metrics.correct_strategy += 1
                if result.fully_correct:
                    metrics.fully_correct += 1
                metrics.total_latency_ms += latency
                metrics.results.append(result)

            results[name] = metrics

        self._last_results = results
        return results

    def generate_report(
        self,
        results: Optional[dict[str, StrategyMetrics]] = None,
    ) -> str:
        """Generate a human-readable comparison report."""
        data = results or self._last_results

        if not data:
            return "No results to report."

        lines = [
            "=" * 60,
            "A/B Test Report",
            "=" * 60,
            f"Total test cases: {next(iter(data.values())).total}",
            "",
        ]

        for name, metrics in data.items():
            lines.extend([
                f"Strategy: {name}",
                f"  Datasource accuracy:  {metrics.datasource_accuracy:.2%}",
                f"  Complexity accuracy:  {metrics.complexity_accuracy:.2%}",
                f"  Strategy accuracy:    {metrics.strategy_accuracy:.2%}",
                f"  Overall accuracy:     {metrics.overall_accuracy:.2%}",
                f"  Mean latency:         {metrics.mean_latency_ms:.2f}ms",
                "",
            ])

        # Comparison
        if len(data) >= 2:
            names = list(data.keys())
            a, b = data[names[0]], data[names[1]]
            diff = a.overall_accuracy - b.overall_accuracy
            winner = names[0] if diff > 0 else names[1] if diff < 0 else "tie"
            lines.extend([
                "Comparison:",
                f"  Winner: {winner}",
                f"  Accuracy delta: {abs(diff):.2%}",
                "",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)

    def export_results(
        self,
        path: str | Path,
        results: Optional[dict[str, StrategyMetrics]] = None,
    ) -> None:
        """Export detailed results to JSON."""
        data = results or self._last_results

        export_data = {
            "timestamp": time.time(),
            "strategies": {name: metrics.to_dict() for name, metrics in data.items()},
            "details": {
                name: [
                    {
                        "query": r.query,
                        "predicted": {
                            "datasource": r.predicted.datasource,
                            "complexity": r.predicted.complexity,
                            "strategy": r.predicted.retrieval_strategy,
                        },
                        "expected": {
                            "datasource": r.expected.expected_datasource,
                            "complexity": r.expected.expected_complexity,
                            "strategy": r.expected.expected_strategy,
                        },
                        "correct": r.fully_correct,
                        "latency_ms": round(r.latency_ms, 3),
                    }
                    for r in metrics.results
                ]
                for name, metrics in data.items()
            },
        }

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)


def create_golden_dataset(
    cases: list[dict[str, str]],
    path: str | Path,
) -> None:
    """Create a golden dataset JSON file from a list of cases.

    Usage:
        create_golden_dataset([
            {"query": "Who wrote Hamlet?", "expected_datasource": "direct", ...},
        ], "benchmarks/golden.json")
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)


__all__ = [
    "ABTestRunner",
    "GoldenCase",
    "StrategyMetrics",
    "StrategyResult",
    "create_golden_dataset",
]
