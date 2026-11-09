"""Measure the running system. Every figure written comes from this run; nothing is estimated.

  python scripts/measure_performance.py run --out docs/performance/phase-5-baseline.json
  python scripts/measure_performance.py latency --label with-x --out results.json
  python scripts/measure_performance.py render docs/performance/phase-5-baseline.json

Runs against the browser-test stack (scripts/e2e_stack.py up), whose database is reseeded
first, so no development data is touched. Inputs are synthetic and generated from a fixed seed;
no PaySim data and nothing from the frozen test partition is used. The production rate limits
stay in place: load is spread across synthetic accounts instead.

`run` measures prediction latency through the browser's cookie-session path (sequential and 8
concurrent clients, twice, to show run-to-run variation), batch throughput at 1,000, 10,000 and
50,000 rows, explorer, dashboard, investigation and export timings at 100,000 and 500,000 stored
predictions, the API container's memory, and frontend bundle sizes. `latency` repeats only the
prediction measurement, for before-and-after comparisons such as M3's rate-limit budget.
"""

import argparse
import gzip
import json
import math
import os
import platform
import random
import secrets
import shutil
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS_FILE = REPO_ROOT / "frontend" / ".e2e" / "accounts.json"
API_URL = os.environ.get("FINGUARD_E2E_API", "http://127.0.0.1:8011")
ORIGIN = "http://127.0.0.1:4173"
CONTAINER = "finguard-api-e2e-1"
SEED = 20261108
TYPES = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")
FINISHED = {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"}
PERF_USERS = 40
CONCURRENCY = 8
BATCH_SIZES = (1_000, 10_000, 50_000)
VOLUMES = (100_000, 500_000)
QUERY_REPEATS = 20


# ---------------------------------------------------------------- statistics


def summarise(samples_ms: list[float]) -> dict[str, float]:
    """Count, mean and nearest-rank percentiles of a list of milliseconds."""
    ordered = sorted(samples_ms)

    def rank(p: float) -> float:
        return ordered[max(math.ceil(p / 100 * len(ordered)) - 1, 0)]

    return {
        "n": len(ordered),
        "mean_ms": round(statistics.fmean(ordered), 2),
        "p50_ms": round(rank(50), 2),
        "p95_ms": round(rank(95), 2),
        "p99_ms": round(rank(99), 2),
        "max_ms": round(ordered[-1], 2),
    }


# ---------------------------------------------------------------- inputs


def synthetic_rows(count: int, prefix: str, rng: random.Random) -> list[dict[str, Any]]:
    """Synthetic transactions in the API's input shape. Merchants receive only PAYMENT."""
    rows = []
    for index in range(count):
        kind = rng.choice(TYPES)
        rows.append(
            {
                "external_transaction_id": f"{prefix}-{index}",
                "amount": f"{rng.uniform(1, 5_000_000):.2f}",
                "transaction_type": kind,
                "step": rng.randint(1, 743),
                "destination_category": "merchant" if kind == "PAYMENT" else "customer",
            }
        )
    return rows


def as_csv(rows: list[dict[str, Any]]) -> bytes:
    header = "external_transaction_id,amount,transaction_type,step,destination_category"
    lines = [header] + [
        f"{r['external_transaction_id']},{r['amount']},{r['transaction_type']},{r['step']},"
        f"{r['destination_category']}"
        for r in rows
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


# ---------------------------------------------------------------- API sessions


def session(email: str, password: str) -> httpx.Client:
    """A client signed in through the cookie-session path the interface uses."""
    client = httpx.Client(base_url=API_URL, headers={"Origin": ORIGIN}, timeout=300)
    response = client.post("/api/v1/auth/session", json={"email": email, "password": password})
    response.raise_for_status()
    client.headers["X-CSRF-Token"] = client.cookies.get("finguard_csrf", path="/")
    return client


def create_perf_users(admin: httpx.Client, run_id: str) -> list[httpx.Client]:
    clients = []
    for index in range(PERF_USERS):
        email = f"perf-{run_id}-{index}@e2e.example.com"
        password = secrets.token_urlsafe(18)
        created = admin.post(
            "/api/v1/users", json={"email": email, "password": password, "role": "analyst"}
        )
        created.raise_for_status()
        clients.append(session(email, password))
    return clients


# ---------------------------------------------------------------- measurements


def prediction_latency(
    clients: list[httpx.Client], rng: random.Random, run_id: str
) -> dict[str, Any]:
    """Sequential and concurrent POST /transactions/predict, each in two rounds."""
    results: dict[str, Any] = {}
    counter = 0

    def one(client: httpx.Client, payload: dict[str, Any]) -> float:
        started = time.perf_counter()
        response = client.post("/api/v1/transactions/predict", json=payload)
        elapsed = (time.perf_counter() - started) * 1000
        if response.status_code != 201:
            raise RuntimeError(f"prediction returned {response.status_code}: {response.text[:200]}")
        return elapsed

    def payloads(count: int) -> list[dict[str, Any]]:
        nonlocal counter
        rows = synthetic_rows(count, f"LAT-{run_id}-{counter}", rng)
        counter += 1
        return rows

    for client, payload in zip(clients, payloads(40), strict=True):  # warm-up, not recorded
        one(client, payload)

    for round_number in (1, 2):
        rows = payloads(400)
        started = time.perf_counter()
        samples = [one(clients[i % len(clients)], row) for i, row in enumerate(rows)]
        wall = time.perf_counter() - started
        results[f"sequential_round_{round_number}"] = {
            **summarise(samples),
            "requests_per_second": round(len(samples) / wall, 1),
        }

        rows = payloads(1_600)
        groups = [clients[k::CONCURRENCY] for k in range(CONCURRENCY)]

        def worker(k: int, rows: list[dict[str, Any]] = rows, groups: list = groups) -> list[float]:
            mine = rows[k::CONCURRENCY]
            return [one(groups[k][i % len(groups[k])], row) for i, row in enumerate(mine)]

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            samples = [ms for chunk in pool.map(worker, range(CONCURRENCY)) for ms in chunk]
        wall = time.perf_counter() - started
        results[f"concurrent_{CONCURRENCY}_round_{round_number}"] = {
            **summarise(samples),
            "requests_per_second": round(len(samples) / wall, 1),
        }
    return results


def run_batch(client: httpx.Client, rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.post(
        "/api/v1/batches/upload", files={"file": (name, as_csv(rows), "text/csv")}
    )
    if response.status_code != 202:
        raise RuntimeError(f"upload returned {response.status_code}: {response.text[:200]}")
    job_id = response.json()["id"]
    while True:
        job = client.get(f"/api/v1/batches/{job_id}").json()
        if job["status"] in FINISHED:
            break
        time.sleep(0.25)
    wall = time.perf_counter() - started
    if job["status"] != "COMPLETED":
        raise RuntimeError(f"batch ended {job['status']}: {job.get('error_message')}")
    server = (
        datetime.fromisoformat(job["completed_at"]) - datetime.fromisoformat(job["created_at"])
    ).total_seconds()
    return {
        "rows": job["total_records"],
        "server_seconds": round(server, 2),
        "client_seconds": round(wall, 2),
        "rows_per_second": round(job["total_records"] / server, 1),
    }


def stored_total(client: httpx.Client) -> int:
    return client.get("/api/v1/transactions", params={"limit": 1}).json()["total"]


def populate(
    clients: list[httpx.Client], target: int, rng: random.Random, run_id: str
) -> list[dict]:
    """Store synthetic predictions through the real batch path until there are `target`."""
    loads = []
    uploader = 0
    while (have := stored_total(clients[0])) < target:
        count = min(50_000, target - have)
        rows = synthetic_rows(count, f"VOL-{run_id}-{have}", rng)
        loads.append(run_batch(clients[uploader % len(clients)], rows, f"volume-{have}.csv"))
        uploader += 1
    return loads


def time_request(client: httpx.Client, path: str, params: dict | None, repeats: int) -> dict:
    for _ in range(2):  # warm-up
        client.get(path, params=params).raise_for_status()
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        response = client.get(path, params=params)
        samples.append((time.perf_counter() - started) * 1000)
        response.raise_for_status()
    return summarise(samples)


def query_timings(client: httpx.Client, total: int, export: bool = True) -> dict[str, Any]:
    """The explorer, dashboard and investigation queries a person triggers, at this volume."""
    queries: dict[str, tuple[str, dict | None]] = {
        "explorer_newest_first": ("/api/v1/transactions", {"limit": 25}),
        "explorer_high_risk": ("/api/v1/transactions", {"limit": 25, "risk_level": "HIGH"}),
        "explorer_type_and_amount": (
            "/api/v1/transactions",
            {"limit": 25, "transaction_type": "TRANSFER", "amount_min": 100000},
        ),
        "explorer_identifier_contains": (
            "/api/v1/transactions",
            {"limit": 25, "external_id": "-4242"},
        ),
        "explorer_highest_score": (
            "/api/v1/transactions",
            {"limit": 25, "sort_by": "model_score", "sort_order": "desc"},
        ),
        "explorer_last_page": ("/api/v1/transactions", {"limit": 25, "offset": max(total - 25, 0)}),
        "dashboard_summary": ("/api/v1/reports/summary", None),
        "investigation_queue_new": ("/api/v1/investigations", {"limit": 25, "status": "NEW"}),
    }
    timings = {
        name: time_request(client, path, params, QUERY_REPEATS)
        for name, (path, params) in queries.items()
    }
    if not export:
        return timings
    exports = []
    size = 0
    for _ in range(3):
        started = time.perf_counter()
        with client.stream(
            "GET", "/api/v1/reports/export", params={"report_type": "predictions"}
        ) as response:
            response.raise_for_status()
            size = sum(len(chunk) for chunk in response.iter_bytes())
        exports.append((time.perf_counter() - started) * 1000)
    timings["predictions_csv_export"] = {**summarise(exports), "bytes": size}
    return timings


def container_memory() -> str | None:
    docker = shutil.which("docker")
    if docker is None:
        return None
    result = subprocess.run(
        [docker, "stats", "--no-stream", "--format", "{{.MemUsage}}", CONTAINER],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or None


def environment() -> dict[str, Any]:
    docker = shutil.which("docker")
    info = {}
    if docker:
        out = (
            subprocess.run(
                [
                    docker,
                    "info",
                    "--format",
                    "{{.NCPU}}|{{.MemTotal}}|{{.ServerVersion}}|{{.OperatingSystem}}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            .stdout.strip()
            .split("|")
        )
        if len(out) == 4:
            info = {
                "cpus": int(out[0]),
                "memory_gib": round(int(out[1]) / 2**30, 1),
                "version": out[2],
                "os": out[3],
            }
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit,
        "host": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "docker_vm": info,
        "api": API_URL,
        "path": "cookie session through the API directly (no proxy)",
        "inputs": f"synthetic, random seed {SEED}",
    }


def bundle_sizes() -> dict[str, Any]:
    assets = REPO_ROOT / "frontend" / "dist" / "assets"
    if not assets.is_dir():
        return {}
    files = {}
    for path in sorted(assets.iterdir()):
        data = path.read_bytes()
        files[path.name] = {"bytes": len(data), "gzip_bytes": len(gzip.compress(data, 9))}
    return files


# ---------------------------------------------------------------- commands


def reseed() -> None:
    subprocess.run(
        [
            sys.executable,
            "-I",
            str(REPO_ROOT / "scripts" / "e2e_database.py"),
            "seed",
            "--out",
            str(ACCOUNTS_FILE),
        ],
        check=True,
    )


def admin_client() -> httpx.Client:
    accounts = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    return session(accounts["admin"]["email"], accounts["admin"]["password"])


def command_run(out: Path) -> int:
    rng = random.Random(SEED)
    run_id = secrets.token_hex(3)
    results: dict[str, Any] = {"environment": environment(), "memory": {}}
    memory: dict[str, Any] = results["memory"]
    reseed()
    memory["after_start"] = container_memory()
    clients = create_perf_users(admin_client(), run_id)

    step(results, "prediction_latency", lambda: prediction_latency(clients, rng, run_id))
    memory["after_predictions"] = container_memory()

    batches = {}
    for size in BATCH_SIZES:
        batches[str(size)] = run_batch(
            clients[size % len(clients)],
            synthetic_rows(size, f"BATCH-{run_id}-{size}", rng),
            f"batch-{size}.csv",
        )
        print(f"batch {size}: {batches[str(size)]}", flush=True)
    results["batch_throughput"] = batches
    memory["after_batches"] = container_memory()

    results["volumes"] = {}
    for target in VOLUMES:
        loads = populate(clients, target, rng, run_id)
        total = stored_total(clients[0])
        print(f"volume {total}: measuring queries", flush=True)
        results["volumes"][str(target)] = {
            "stored_predictions": total,
            "loads": loads,
            "queries": query_timings(clients[0], total),
        }
        memory[f"after_{target}"] = container_memory()

    results["bundle"] = bundle_sizes()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def step(results: dict[str, Any], name: str, action: Callable[[], Any]) -> None:
    print(f"measuring {name}", flush=True)
    results[name] = action()
    print(json.dumps(results[name], indent=2), flush=True)


def command_queries(label: str, out: Path, export: bool) -> int:
    """Time the queries at the volume already stored, without reseeding: for before and after."""
    client = admin_client()
    total = stored_total(client)
    result = {
        "label": label,
        "environment": environment(),
        "stored_predictions": total,
        "queries": query_timings(client, total, export),
        "memory": container_memory(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["queries"], indent=2))
    return 0


def command_batches(label: str, out: Path) -> int:
    """Batch throughput only, at 1,000, 10,000 and 50,000 rows, after reseeding."""
    rng = random.Random(SEED)
    run_id = secrets.token_hex(3)
    reseed()
    clients = create_perf_users(admin_client(), run_id)
    batches = {}
    for size in BATCH_SIZES:
        rows = synthetic_rows(size, f"BATCH-{run_id}-{size}", rng)
        batches[str(size)] = run_batch(clients[size % len(clients)], rows, f"batch-{size}.csv")
    result = {"label": label, "environment": environment(), "batch_throughput": batches}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(batches, indent=2))
    return 0


def command_latency(label: str, out: Path) -> int:
    rng = random.Random(SEED)
    run_id = secrets.token_hex(3)
    reseed()
    clients = create_perf_users(admin_client(), run_id)
    result = {
        "label": label,
        "environment": environment(),
        "prediction_latency": prediction_latency(clients, rng, run_id),
        "memory_after": container_memory(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["prediction_latency"], indent=2))
    return 0


# The M3 budget, fixed in docs/performance/phase-5-baseline.md before any M3 code was written.
BUDGET = {"p50_ms": 0.10, "p95_ms": 0.15}
BUDGET_FLOOR_MS = 2.0


def compare_runs(baseline: list[dict], candidate: list[dict]) -> dict[str, Any]:
    """Apply the budget: for each mode and statistic, the median over all runs and rounds."""
    checks = {}
    for mode in ("sequential", "concurrent"):
        for statistic, share in BUDGET.items():

            def median_of(runs: list[dict], mode: str = mode, statistic: str = statistic) -> float:
                return statistics.median(
                    values[statistic]
                    for run in runs
                    for name, values in run["prediction_latency"].items()
                    if name.startswith(mode)
                )

            a, b = median_of(baseline), median_of(candidate)
            allowed = max(share * a, BUDGET_FLOOR_MS)
            checks[f"{mode}_{statistic}"] = {
                "baseline_ms": round(a, 2),
                "candidate_ms": round(b, 2),
                "overhead_ms": round(b - a, 2),
                "allowed_ms": round(allowed, 2),
                "within_budget": b - a <= allowed,
            }
    return {"checks": checks, "accepted": all(c["within_budget"] for c in checks.values())}


def command_compare(baseline: list[Path], candidate: list[Path], out: Path) -> int:
    def load(paths: list[Path]) -> list[dict]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    result = {
        "rule": "overhead <= max(share x baseline, 2 ms); share 10% for p50, 15% for p95",
        "baseline_runs": [path.name for path in baseline],
        "candidate_runs": [path.name for path in candidate],
        **compare_runs(load(baseline), load(candidate)),
    }
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["accepted"] else 1


def command_render(source: Path, pages: Path | None) -> int:
    page_results = json.loads(pages.read_text(encoding="utf-8")) if pages else None
    print(render(json.loads(source.read_text(encoding="utf-8")), source.name, page_results), end="")
    return 0


def row(*cells: Any) -> str:
    """One Markdown table row."""
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def render(results: dict[str, Any], source_name: str, pages: dict[str, Any] | None = None) -> str:
    """Markdown tables generated only from a saved results file."""
    env = results["environment"]
    host, vm = env["host"], env["docker_vm"]
    lines = [
        f"<!-- Generated by scripts/measure_performance.py render from {source_name}. "
        "Do not edit by hand. -->",
        "",
        f"Measured {env['measured_at']} at commit `{env['git_commit']}`. "
        f"Host: {host['platform']}, {host['logical_cpus']} logical CPUs. "
        f"Docker VM: {vm.get('cpus')} CPUs, {vm.get('memory_gib')} GiB, "
        f"Docker {vm.get('version')}. Path: {env['path']}. Inputs: {env['inputs']}.",
        "",
        "### Prediction latency (POST /api/v1/transactions/predict)",
        "",
        row("Run", "n", "p50 ms", "p95 ms", "p99 ms", "max ms", "requests/s"),
        row(*["---"] * 7),
    ]
    for name, s in results["prediction_latency"].items():
        lines.append(
            row(
                name,
                s["n"],
                s["p50_ms"],
                s["p95_ms"],
                s["p99_ms"],
                s["max_ms"],
                s["requests_per_second"],
            )
        )
    if "batch_throughput" in results:
        lines += ["", "### Batch throughput", ""]
        lines += [
            row("Rows", "Server seconds", "Rows per second", "Client seconds"),
            row(*["---"] * 4),
        ]
        for size, b in results["batch_throughput"].items():
            lines.append(
                row(
                    f"{int(size):,}",
                    b["server_seconds"],
                    f"{b['rows_per_second']:,}",
                    b["client_seconds"],
                )
            )
    for volume in results.get("volumes", {}).values():
        lines += ["", f"### Queries at {volume['stored_predictions']:,} stored predictions", ""]
        lines += [row("Query", "n", "p50 ms", "p95 ms", "max ms"), row(*["---"] * 5)]
        for name, s in volume["queries"].items():
            extra = f" ({s['bytes']:,} bytes)" if "bytes" in s else ""
            lines.append(row(f"{name}{extra}", s["n"], s["p50_ms"], s["p95_ms"], s["max_ms"]))
    if results.get("memory"):
        lines += [
            "",
            "### API container memory (docker stats)",
            "",
            "| Point | Usage |",
            "|---|---|",
        ]
        for point, usage in results["memory"].items():
            lines.append(f"| {point} | {usage} |")
    if results.get("bundle"):
        lines += ["", "### Frontend bundle", "", "| File | Bytes | Gzip bytes |", "|---|---|---|"]
        for name, size in results["bundle"].items():
            lines.append(f"| `{name}` | {size['bytes']:,} | {size['gzip_bytes']:,} |")
    if pages:
        lines += [
            "",
            f"### Page readiness ({pages['browser']}, {pages['viewport']}, {pages['measured_at']})",
            "",
            "Time from navigation start until the heading shows and no loading state remains.",
            "",
            row(
                "Page",
                "Cold median ms",
                "Cold max ms",
                "Warm median ms",
                "Warm max ms",
                "Cold bytes",
            ),
            row(*["---"] * 6),
        ]
        for page, t in pages["pages"].items():
            lines.append(
                row(
                    page,
                    t["cold_ready_ms_median"],
                    t["cold_ready_ms_max"],
                    t["warm_ready_ms_median"],
                    t["warm_ready_ms_max"],
                    f"{t['cold_transferred_bytes_median']:,}",
                )
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--out", type=Path, required=True)
    queries = commands.add_parser("queries")
    queries.add_argument("--label", required=True)
    queries.add_argument("--out", type=Path, required=True)
    queries.add_argument("--no-export", action="store_true")
    batches = commands.add_parser("batches")
    batches.add_argument("--label", required=True)
    batches.add_argument("--out", type=Path, required=True)
    latency = commands.add_parser("latency")
    latency.add_argument("--label", required=True)
    latency.add_argument("--out", type=Path, required=True)
    show = commands.add_parser("render")
    show.add_argument("source", type=Path)
    show.add_argument("--pages", type=Path, help="page timings from playwright.perf.config.ts")
    compare = commands.add_parser("compare", help="apply the M3 latency budget to paired runs")
    compare.add_argument("--baseline", type=Path, nargs="+", required=True)
    compare.add_argument("--candidate", type=Path, nargs="+", required=True)
    compare.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.command == "run":
        return command_run(arguments.out)
    if arguments.command == "compare":
        return command_compare(arguments.baseline, arguments.candidate, arguments.out)
    if arguments.command == "queries":
        return command_queries(arguments.label, arguments.out, not arguments.no_export)
    if arguments.command == "batches":
        return command_batches(arguments.label, arguments.out)
    if arguments.command == "latency":
        return command_latency(arguments.label, arguments.out)
    return command_render(arguments.source, arguments.pages)


if __name__ == "__main__":
    sys.exit(main())
