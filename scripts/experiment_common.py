"""Shared helpers for deterministic, CPU-only TPP experiments."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence


RAW_FIELDS = (
    "instance",
    "source",
    "market_count",
    "item_count",
    "algorithm",
    "seed",
    "k_max",
    "lambda_max",
    "delta_add",
    "delta_drop",
    "delta_exchange",
    "alpha",
    "route",
    "item_markets",
    "travel_cost",
    "purchase_cost",
    "total_cost",
    "best_known_cost",
    "gap_percent",
    "feasible",
    "iterations",
    "perturbations",
    "diversity_restarts",
    "elapsed_seconds",
    "error",
)

SUMMARY_FIELDS = (
    "instance",
    "source",
    "algorithm",
    "k_max",
    "lambda_max",
    "delta_add",
    "delta_drop",
    "delta_exchange",
    "alpha",
    "runs",
    "feasible_runs",
    "feasible_rate_percent",
    "best_cost",
    "mean_cost",
    "cost_stdev",
    "best_gap_percent",
    "mean_gap_percent",
    "mean_elapsed_seconds",
)

ALGORITHM_SUMMARY_FIELDS = (
    "algorithm",
    "k_max",
    "lambda_max",
    "delta_add",
    "delta_drop",
    "delta_exchange",
    "alpha",
    "instances",
    "runs",
    "feasible_runs",
    "feasible_rate_percent",
    "best_gap_percent",
    "mean_gap_percent",
    "mean_elapsed_seconds",
)


def discover_instance_files(inputs: Sequence[str]) -> list[Path]:
    """Expand JSON files and directories into a stable, duplicate-free list."""

    discovered: list[Path] = []
    for raw_path in inputs:
        path = Path(raw_path).expanduser()
        if path.is_file():
            if path.suffix.lower() != ".json":
                raise ValueError(f"Instance file must use .json: {path}")
            discovered.append(path.resolve())
        elif path.is_dir():
            discovered.extend(candidate.resolve() for candidate in path.rglob("*.json"))
        else:
            raise ValueError(f"Instance path does not exist: {path}")

    unique = sorted(set(discovered), key=lambda candidate: str(candidate))
    if not unique:
        raise ValueError("No JSON instances were found.")
    return unique


def parse_seeds(value: str) -> tuple[int, ...]:
    """Parse a comma-separated seed list while preserving input order."""

    try:
        seeds = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise ValueError("Seeds must be comma-separated integers.") from exc
    if not seeds:
        raise ValueError("At least one seed is required.")
    if len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must not contain duplicates.")
    return seeds


def load_reference_costs(path: str | None) -> dict[str, float]:
    """Load optional best-known costs keyed by the JSON instance name."""

    if path is None:
        return {}
    source = Path(path)
    with source.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"instance", "best_known_cost"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(
                "Known-best CSV must contain instance and best_known_cost columns."
            )
        references: dict[str, float] = {}
        for line_number, row in enumerate(reader, start=2):
            name = (row.get("instance") or "").strip()
            if not name:
                raise ValueError(f"Known-best CSV line {line_number} has no instance name.")
            if name in references:
                raise ValueError(f"Duplicate known-best entry for instance {name!r}.")
            try:
                cost = float(row["best_known_cost"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Known-best CSV line {line_number} has an invalid cost."
                ) from exc
            if not math.isfinite(cost) or cost <= 0:
                raise ValueError("Best-known costs must be finite and greater than zero.")
            references[name] = cost
    return references


def calculate_gap(cost: float, reference: float | None) -> float | None:
    if reference is None:
        return None
    return 100.0 * (cost - reference) / reference


def encode_int_sequence(values: Iterable[int]) -> str:
    return json.dumps(list(values), separators=(",", ":"))


def decode_int_sequence(value: str, field_name: str) -> tuple[int, ...]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be a JSON integer array.") from exc
    if not isinstance(payload, list) or any(
        not isinstance(item, int) or isinstance(item, bool) for item in payload
    ):
        raise ValueError(f"{field_name} must be a JSON integer array.")
    return tuple(payload)


def format_number(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    return format(value, ".12g")


def parse_optional_float(value: str | None, field_name: str) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite.")
    return parsed


def parse_bool(value: str | None, field_name: str = "value") -> bool:
    normalized = (value or "").strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{field_name} must be true or false.")


def read_csv_rows(path: str | Path, required_fields: Sequence[str]) -> list[dict[str, str]]:
    source = Path(path)
    with source.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required_fields) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def write_csv_rows(
    path: str | Path,
    fields: Sequence[str],
    rows: Iterable[Mapping[str, object]],
    *,
    append: bool = False,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_header = not append or not destination.exists() or destination.stat().st_size == 0
    mode = "a" if append else "w"
    with destination.open(mode, encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _mean(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _sample_stdev(values: Sequence[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def summarize_records(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Aggregate raw runs per instance, algorithm, and parameter configuration."""

    key_fields = (
        "instance",
        "source",
        "algorithm",
        "k_max",
        "lambda_max",
        "delta_add",
        "delta_drop",
        "delta_exchange",
        "alpha",
    )
    grouped: dict[tuple[str, ...], list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field, "") for field in key_fields)].append(row)

    summaries: list[dict[str, str]] = []
    for key in sorted(grouped):
        group = grouped[key]
        feasible = [row for row in group if parse_bool(row.get("feasible"), "feasible")]
        costs = [
            float(row["total_cost"])
            for row in feasible
            if row.get("total_cost", "").strip()
        ]
        elapsed = [
            float(row["elapsed_seconds"])
            for row in feasible
            if row.get("elapsed_seconds", "").strip()
        ]
        gaps = [
            float(row["gap_percent"])
            for row in feasible
            if row.get("gap_percent", "").strip()
        ]
        values = dict(zip(key_fields, key))
        values.update(
            {
                "runs": str(len(group)),
                "feasible_runs": str(len(feasible)),
                "feasible_rate_percent": format_number(100.0 * len(feasible) / len(group)),
                "best_cost": format_number(min(costs) if costs else None),
                "mean_cost": format_number(_mean(costs)),
                "cost_stdev": format_number(_sample_stdev(costs)),
                "best_gap_percent": format_number(min(gaps) if gaps else None),
                "mean_gap_percent": format_number(_mean(gaps)),
                "mean_elapsed_seconds": format_number(_mean(elapsed)),
            }
        )
        summaries.append(values)
    return summaries


def summarize_algorithms(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Aggregate scale-independent metrics across instances for each configuration."""

    key_fields = (
        "algorithm",
        "k_max",
        "lambda_max",
        "delta_add",
        "delta_drop",
        "delta_exchange",
        "alpha",
    )
    grouped: dict[tuple[str, ...], list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field, "") for field in key_fields)].append(row)

    summaries: list[dict[str, str]] = []
    for key in sorted(grouped):
        group = grouped[key]
        feasible = [row for row in group if parse_bool(row.get("feasible"), "feasible")]
        elapsed = [
            float(row["elapsed_seconds"])
            for row in feasible
            if row.get("elapsed_seconds", "").strip()
        ]
        gaps = [
            float(row["gap_percent"])
            for row in feasible
            if row.get("gap_percent", "").strip()
        ]
        values = dict(zip(key_fields, key))
        values.update(
            {
                "instances": str(len({row.get("source", "") for row in group})),
                "runs": str(len(group)),
                "feasible_runs": str(len(feasible)),
                "feasible_rate_percent": format_number(100.0 * len(feasible) / len(group)),
                "best_gap_percent": format_number(min(gaps) if gaps else None),
                "mean_gap_percent": format_number(_mean(gaps)),
                "mean_elapsed_seconds": format_number(_mean(elapsed)),
            }
        )
        summaries.append(values)
    return summaries
