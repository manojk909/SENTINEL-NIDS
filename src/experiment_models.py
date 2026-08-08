"""Comparative analysis — 8 model configurations on IDENTICAL splits.

Metric of record is macro-F1 and per-class recall on the official KDDTest+ split, NOT accuracy.
Rationale: the two most severe attack families (R2L, U2R) are 0.83% of training data, so a model
that ignores them entirely still scores highly on accuracy.

Also reports 3-fold stratified CV macro-F1 on KDDTrain+ so in-distribution stability can be
separated from the distribution-shift penalty.

Crash-safe by design: every model's metrics are written to reports/metrics/models/<name>.json
the moment that model finishes, and a completed model is skipped on re-run. A failure in model N
can never cost models 1..N-1.

Writes:  reports/metrics/model_comparison.json
         reports/metrics/models/<name>.json   (per-model checkpoints)
         models/<name>.joblib                 (fitted estimators)
"""
from __future__ import annotations

import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, recall_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from config import FAMILIES, METRICS, MODELS, SEED
from data import build_feature_matrix, load_raw

warnings.filterwarnings("ignore")

CV_FOLDS = 3


def model_zoo() -> dict:
    """8 configurations. The 'balanced' variant exists to test whether the rare-class
    collapse is merely an artefact of loss weighting (result: it is not)."""
    return {
        "00_baseline_majority": DummyClassifier(strategy="most_frequent"),
        "01_logistic_regression": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, n_jobs=-1, random_state=SEED)),
        ]),
        "02_decision_tree": DecisionTreeClassifier(
            max_depth=20, min_samples_leaf=5, random_state=SEED),
        "03_random_forest": RandomForestClassifier(
            n_estimators=300, n_jobs=-1, random_state=SEED),
        "04_random_forest_balanced": RandomForestClassifier(
            n_estimators=300, n_jobs=-1, random_state=SEED,
            class_weight="balanced_subsample"),
        "05_xgboost": XGBClassifier(
            n_estimators=400, max_depth=8, learning_rate=0.1, subsample=0.9,
            colsample_bytree=0.9, tree_method="hist", n_jobs=-1,
            random_state=SEED, eval_metric="mlogloss"),
        "06_lightgbm": LGBMClassifier(
            n_estimators=400, num_leaves=63, learning_rate=0.1, n_jobs=-1,
            random_state=SEED, verbose=-1),
        # NOTE: early_stopping=True crashes in scikit-learn 1.8.0 when y holds string
        # labels (the internal _score path calls np.isnan on a string array). We pass
        # integer labels to every model uniformly, which also sidesteps it; n_iter_no_change
        # gives convergence control without the validation-split code path.
        "07_mlp": Pipeline([
            ("scale", StandardScaler()),
            ("clf", MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=60,
                                  early_stopping=False, n_iter_no_change=8,
                                  random_state=SEED)),
        ]),
    }


def evaluate(y_true, y_pred, labels) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro",
                                         labels=labels, zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_true, y_pred, average="weighted",
                                            labels=labels, zero_division=0)), 4),
        "per_class_recall": {
            c: round(float(r), 4) for c, r in zip(labels, recall_score(
                y_true, y_pred, average=None, labels=labels, zero_division=0))},
        "per_class_f1": {
            c: round(float(r), 4) for c, r in zip(labels, f1_score(
                y_true, y_pred, average=None, labels=labels, zero_division=0))},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def binary_view(y_family_true, y_family_pred) -> dict:
    """What an operator actually sees: did the alarm fire or not?"""
    yt = (np.asarray(y_family_true) != "Normal").astype(int)
    yp = (np.asarray(y_family_pred) != "Normal").astype(int)
    tn, fp, fn, tp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
    return {
        "detection_rate": round(float(tp / max(1, tp + fn)), 4),
        "false_alarm_rate": round(float(fp / max(1, fp + tn)), 4),
        "precision": round(float(tp / max(1, tp + fp)), 4),
        "f1": round(float(2 * tp / max(1, 2 * tp + fp + fn)), 4),
        "missed_attacks": int(fn),
        "false_alarms": int(fp),
    }


def main() -> dict:
    train_df, test_df = load_raw("train"), load_raw("test")
    (Xtr, Xte), feat_names, vocab = build_feature_matrix(train_df, test_df)
    ytr, yte = train_df["family"].values, test_df["family"].values

    # Integer targets for EVERY model: XGBoost requires them, and sklearn 1.8.0's MLP
    # crashes on string labels. Predictions map back to family names before scoring.
    fam_to_int = {f: i for i, f in enumerate(FAMILIES)}
    int_to_fam = {i: f for f, i in fam_to_int.items()}
    ytr_i = np.array([fam_to_int[v] for v in ytr])

    ckpt = METRICS / "models"
    ckpt.mkdir(parents=True, exist_ok=True)

    joblib.dump({"feature_names": feat_names, "vocab": vocab, "families": FAMILIES},
                MODELS / "preprocessor_meta.joblib")

    results = {
        "protocol": "train on KDDTrain+ (125,973) -> test on KDDTest+ (22,544)",
        "n_features": len(feat_names),
        "cv_folds_on_train": CV_FOLDS,
        "metric_of_record": "macro_f1 on official test split",
        "models": {},
    }
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)

    for name, model in model_zoo().items():
        ck = ckpt / f"{name}.json"
        if ck.exists():
            results["models"][name] = json.loads(ck.read_text())
            print(f"[{name}] cached -> skipping (delete {ck.name} to force rerun)", flush=True)
            continue

        print(f"\n[{name}] fitting ...", flush=True)
        try:
            t0 = time.time()
            model.fit(Xtr, ytr_i)
            fit_s = time.time() - t0

            t0 = time.time()
            raw_pred = model.predict(Xte)
            pred_s = time.time() - t0
            pred = np.array([int_to_fam[int(v)] for v in raw_pred])
        except Exception as e:
            print(f"[{name}] FAILED: {type(e).__name__}: {e}", flush=True)
            results["models"][name] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
            ck.write_text(json.dumps(results["models"][name], indent=2))
            continue

        entry = evaluate(yte, pred, FAMILIES)
        entry["binary_detection"] = binary_view(yte, pred)
        entry["fit_seconds"] = round(fit_s, 2)
        entry["predict_seconds_22544_flows"] = round(pred_s, 4)
        entry["predict_ms_per_flow"] = round(pred_s / len(Xte) * 1000, 5)

        # In-distribution CV on the training split only — isolates the shift penalty.
        t0 = time.time()
        try:
            cv = cross_val_score(model_zoo()[name], Xtr, ytr_i, cv=skf,
                                 scoring="f1_macro", n_jobs=1)
            entry["cv_macro_f1_mean_on_train"] = round(float(cv.mean()), 4)
            entry["cv_macro_f1_std_on_train"] = round(float(cv.std()), 4)
            entry["cv_seconds"] = round(time.time() - t0, 1)
            entry["shift_penalty_macro_f1"] = round(float(cv.mean()) - entry["macro_f1"], 4)
        except Exception as e:
            entry["cv_error"] = str(e)[:200]

        te = test_df.copy()
        te["pred"] = pred
        nov = te[te.is_novel == 1]
        entry["novel_attacks"] = {
            "n": int(len(nov)),
            "detected_as_attack_rate": round(float((nov["pred"] != "Normal").mean()), 4),
            "missed_as_normal_rate": round(float((nov["pred"] == "Normal").mean()), 4),
            "correct_family_rate": round(float((nov["pred"] == nov["family"]).mean()), 4),
        }
        seen = te[(te.is_attack == 1) & (te.is_novel == 0)]
        entry["seen_attacks"] = {
            "n": int(len(seen)),
            "detected_as_attack_rate": round(float((seen["pred"] != "Normal").mean()), 4),
            "correct_family_rate": round(float((seen["pred"] == seen["family"]).mean()), 4),
        }

        joblib.dump(model, MODELS / f"{name}.joblib")
        results["models"][name] = entry
        # CHECKPOINT: persist immediately, both per-model and the rolling aggregate.
        ck.write_text(json.dumps(entry, indent=2))
        (METRICS / "model_comparison.json").write_text(json.dumps(results, indent=2))

        print(f"[{name}] macro-F1 {entry['macro_f1']:.4f}  acc {entry['accuracy']:.4f}  "
              f"detect {entry['binary_detection']['detection_rate']:.3f}  "
              f"FAR {entry['binary_detection']['false_alarm_rate']:.3f}  "
              f"({fit_s:.1f}s)", flush=True)

    ok = {k: v for k, v in results["models"].items() if "macro_f1" in v}
    results["best_by_macro_f1"] = max(ok, key=lambda k: ok[k]["macro_f1"]) if ok else None
    (METRICS / "model_comparison.json").write_text(json.dumps(results, indent=2))
    print(f"\n[models] best by macro-F1: {results['best_by_macro_f1']}")
    return results


if __name__ == "__main__":
    r = main()
    rows = []
    for n, m in r["models"].items():
        if "macro_f1" not in m:
            print(f"  !! {n}: {m.get('error')}")
            continue
        rows.append({
            "model": n,
            "macro_F1": m["macro_f1"],
            "accuracy": m["accuracy"],
            "bal_acc": m["balanced_accuracy"],
            "CV_F1_train": m.get("cv_macro_f1_mean_on_train"),
            "shift_pen": m.get("shift_penalty_macro_f1"),
            "detect": m["binary_detection"]["detection_rate"],
            "FAR": m["binary_detection"]["false_alarm_rate"],
            "R2L_rec": m["per_class_recall"]["R2L"],
            "U2R_rec": m["per_class_recall"]["U2R"],
            "novel_miss": m["novel_attacks"]["missed_as_normal_rate"],
            "ms/flow": m["predict_ms_per_flow"],
        })
    print("\n" + pd.DataFrame(rows).to_string(index=False))
