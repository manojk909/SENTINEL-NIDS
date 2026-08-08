#!/usr/bin/env python3
"""SENTINEL-NIDS — one-command reproduction.

Runs the full pipeline in dependency order. Every stage is idempotent: completed work is
detected and skipped, so an interrupted run resumes rather than restarting.

    python run_all.py                 # run everything that is not already done
    python run_all.py --force         # ignore checkpoints, recompute from scratch
    python run_all.py --only models   # run a single stage by name

Expected total runtime on 2 vCPU: ~12 minutes cold, seconds when fully cached.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
METRICS = ROOT / "reports" / "metrics"

# (name, script, sentinel output that means "already done")
STAGES = [
    ("data",     "data.py",                ROOT / "data" / "processed" / "dataset_summary.json"),
    ("leakage",  "experiment_leakage.py",  METRICS / "leakage_experiment.json"),
    ("models",   "experiment_models.py",   METRICS / "model_comparison.json"),
    ("zeroday",  "experiment_zeroday.py",  METRICS / "zeroday_experiment.json"),
    ("explain",  "explain.py",             METRICS / "explainability.json"),
    ("deploy",   "deploy_benchmark.py",    METRICS / "deployment_benchmark.json"),
    ("plots",    "plots.py",               ROOT / "reports" / "figures" / "fig9_lofo.png"),
]


def run(script: str) -> int:
    print(f"\n{'=' * 74}\n  RUNNING  {script}\n{'=' * 74}", flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, "-u", script], cwd=SRC)
    print(f"  -> {script} exited {r.returncode} after {time.time() - t0:.1f}s", flush=True)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="recompute even if outputs already exist")
    ap.add_argument("--only", default=None,
                    help="run only this stage: " + ", ".join(n for n, _, _ in STAGES))
    args = ap.parse_args()

    todo = STAGES if args.only is None else [s for s in STAGES if s[0] == args.only]
    if not todo:
        print(f"unknown stage {args.only!r}; choose from "
              f"{[n for n, _, _ in STAGES]}", file=sys.stderr)
        return 2

    failed = []
    t_start = time.time()
    for name, script, sentinel in todo:
        if sentinel.exists() and not args.force:
            print(f"[skip] {name:<8} already done ({sentinel.relative_to(ROOT)})")
            continue
        # plots must run last and needs the metrics; a failure there is not fatal to
        # the rest, so we record and continue rather than aborting the pipeline.
        if run(script) != 0:
            failed.append(name)

    print(f"\n{'=' * 74}")
    print(f"  total wall time: {time.time() - t_start:.1f}s")
    if failed:
        print(f"  FAILED stages: {', '.join(failed)}")
        print("  (per-stage checkpoints are preserved — re-run to resume)")
    else:
        print("  all stages complete")
    print(f"  metrics -> {METRICS.relative_to(ROOT)}")
    print(f"  figures -> {(ROOT / 'reports' / 'figures').relative_to(ROOT)}")
    print("=" * 74)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
