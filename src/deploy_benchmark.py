"""Deployment considerations — measured, not asserted.

An intrusion detector is a latency-bound service: it must classify a flow before the next
one arrives. A model that is 2 points better but 50x slower is worse in production. So we
measure what actually constrains deployment:

  1. Per-flow inference latency (p50/p95/p99) — single-flow, the real serving pattern.
  2. Batch throughput (flows/second) — for offline replay and backfill.
  3. Serialised model size on disk — matters for edge/appliance deployment.
  4. ONNX export + ONNX Runtime latency — the realistic production path (no Python
     dependency, portable to C++/Rust/Go services).
  5. Cold-start / load time.

Writes reports/metrics/deployment_benchmark.json
       models/sentinel_best.onnx
"""
from __future__ import annotations

import json
import os
import time

import joblib
import numpy as np

from config import FAMILIES, METRICS, MODELS, SEED
from data import build_feature_matrix, load_raw

N_SINGLE = 400        # single-flow latency samples
BATCH_SIZES = [1, 32, 256, 4096]


def percentiles(xs) -> dict:
    a = np.asarray(xs) * 1000.0  # -> ms
    return {
        "p50_ms": round(float(np.percentile(a, 50)), 4),
        "p95_ms": round(float(np.percentile(a, 95)), 4),
        "p99_ms": round(float(np.percentile(a, 99)), 4),
        "mean_ms": round(float(a.mean()), 4),
    }


def main() -> dict:
    train_df, test_df = load_raw("train"), load_raw("test")
    (Xtr, Xte), feat_names, _ = build_feature_matrix(train_df, test_df)
    Xte_np = Xte.values.astype(np.float32)

    out = {"n_features": len(feat_names),
           "note": "Measured on the build container CPU. Absolute numbers are "
                   "hardware-dependent; the RATIOS between models are the transferable "
                   "result."}

    # Report cpu info so the numbers are interpretable.
    try:
        import platform
        out["platform"] = {"machine": platform.machine(),
                           "processor": platform.processor() or "unknown",
                           "python": platform.python_version(),
                           "cpu_count": os.cpu_count()}
    except Exception:
        pass

    candidates = ["01_logistic_regression", "02_decision_tree", "03_random_forest",
                  "05_xgboost", "06_lightgbm", "07_mlp"]
    rng = np.random.default_rng(SEED)
    sample_idx = rng.choice(len(Xte_np), size=N_SINGLE, replace=False)

    out["models"] = {}
    for name in candidates:
        p = MODELS / f"{name}.joblib"
        if not p.exists():
            continue
        t0 = time.perf_counter()
        model = joblib.load(p)
        load_s = time.perf_counter() - t0

        entry = {
            "disk_size_kb": round(p.stat().st_size / 1024, 1),
            "load_seconds": round(load_s, 4),
        }

        # Warm up (first call allocates buffers / JITs).
        model.predict(Xte_np[:8])

        # --- single-flow latency: the real serving pattern ---
        lat = []
        for i in sample_idx:
            row = Xte_np[i:i + 1]
            t0 = time.perf_counter()
            model.predict(row)
            lat.append(time.perf_counter() - t0)
        entry["single_flow_latency"] = percentiles(lat)

        # --- batch throughput ---
        tp = {}
        for b in BATCH_SIZES:
            X = Xte_np[:b]
            t0 = time.perf_counter()
            reps = max(1, int(2000 / b))
            for _ in range(reps):
                model.predict(X)
            el = (time.perf_counter() - t0) / reps
            tp[f"batch_{b}"] = {
                "seconds_per_batch": round(el, 6),
                "flows_per_second": int(b / el) if el > 0 else None,
            }
        entry["batch_throughput"] = tp
        out["models"][name] = entry
        print(f"[deploy] {name:<24} p50 {entry['single_flow_latency']['p50_ms']:.3f} ms  "
              f"p99 {entry['single_flow_latency']['p99_ms']:.3f} ms  "
              f"{entry['disk_size_kb']:>8.1f} KB  "
              f"{tp['batch_4096']['flows_per_second']:>9,} flows/s (batch 4096)", flush=True)
        (METRICS / "deployment_benchmark.json").write_text(json.dumps(out, indent=2))

    # ---------------- ONNX export: the realistic production path ----------------
    try:
        from skl2onnx import to_onnx
        import onnxruntime as ort

        src = MODELS / "01_logistic_regression.joblib"
        if src.exists():
            model = joblib.load(src)
            onx = to_onnx(model, Xte_np[:1], target_opset=17)
            opath = MODELS / "sentinel_best.onnx"
            opath.write_bytes(onx.SerializeToString())

            so = ort.SessionOptions()
            so.intra_op_num_threads = 1  # single-threaded: the honest per-request setting
            sess = ort.InferenceSession(opath.read_bytes(), so,
                                        providers=["CPUExecutionProvider"])
            iname = sess.get_inputs()[0].name
            sess.run(None, {iname: Xte_np[:8]})  # warm up

            lat = []
            for i in sample_idx:
                row = Xte_np[i:i + 1]
                t0 = time.perf_counter()
                sess.run(None, {iname: row})
                lat.append(time.perf_counter() - t0)

            t0 = time.perf_counter()
            for _ in range(20):
                sess.run(None, {iname: Xte_np[:4096]})
            batch_el = (time.perf_counter() - t0) / 20

            out["onnx_runtime"] = {
                "source_model": "01_logistic_regression",
                "file": "models/sentinel_best.onnx",
                "disk_size_kb": round(opath.stat().st_size / 1024, 1),
                "intra_op_threads": 1,
                "single_flow_latency": percentiles(lat),
                "batch_4096_flows_per_second": int(4096 / batch_el),
            }
            print(f"[deploy] ONNX Runtime          p50 "
                  f"{out['onnx_runtime']['single_flow_latency']['p50_ms']:.3f} ms  "
                  f"{out['onnx_runtime']['disk_size_kb']:.1f} KB  "
                  f"{out['onnx_runtime']['batch_4096_flows_per_second']:,} flows/s", flush=True)
    except Exception as e:
        out["onnx_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        print(f"[deploy] ONNX export failed: {e}", flush=True)

    # ---------------- Line-rate context ----------------
    # A 1 Gbps link with an average flow of ~1 KB is on the order of 10^5 flows/s in the
    # worst case; typical enterprise egress is far lower. We state the arithmetic so the
    # claim is checkable rather than hand-waved.
    best = None
    if "onnx_runtime" in out:
        best = out["onnx_runtime"]["batch_4096_flows_per_second"]
    out["capacity_context"] = {
        "best_batch_throughput_flows_per_second": best,
        "assumption": "Flow-level (not packet-level) classification. NSL-KDD features are "
                      "aggregates over a completed flow, so the detector runs once per "
                      "flow, not once per packet.",
        "implication": "Single-threaded batch throughput above ~10^5 flows/s covers a "
                       "1 Gbps link under a conservative 1 KB mean flow size; a single "
                       "commodity core is therefore sufficient at campus/edge scale. The "
                       "binding cost in practice is FEATURE EXTRACTION from the packet "
                       "stream, not model inference — a point most ML-IDS papers omit.",
    }

    (METRICS / "deployment_benchmark.json").write_text(json.dumps(out, indent=2))
    print(f"\n[deploy] written -> {METRICS / 'deployment_benchmark.json'}")
    return out


if __name__ == "__main__":
    main()
