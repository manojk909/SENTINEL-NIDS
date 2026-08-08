"""THE HEADLINE EXPERIMENT.

One model. One preprocessing pipeline. One hyperparameter set. Two evaluation protocols.

  Protocol A ("the tutorial protocol"): pool KDDTrain+ and KDDTest+, shuffle, split 80/20.
  Protocol B ("the honest protocol"):   train on KDDTrain+, test on KDDTest+ as designed.

Everything except the split is held constant, so any difference in the reported score is
attributable to the evaluation protocol alone.

Writes reports/metrics/leakage_experiment.json
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             classification_report, confusion_matrix, f1_score,
                             recall_score)
from sklearn.model_selection import train_test_split

from config import FAMILIES, METRICS, SEED
from data import build_feature_matrix, load_raw


def rf():
    """Identical model in both protocols. Deliberately unremarkable settings."""
    return RandomForestClassifier(
        n_estimators=200, max_depth=None, n_jobs=-1, random_state=SEED,
        class_weight=None,
    )


def score(y_true, y_pred, labels) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro",
                                         labels=labels, zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_true, y_pred, average="weighted",
                                            labels=labels, zero_division=0)), 4),
        "per_class_recall": {
            c: round(float(r), 4) for c, r in zip(
                labels, recall_score(y_true, y_pred, average=None, labels=labels,
                                     zero_division=0))
        },
        "per_class_support": {
            c: int((np.asarray(y_true) == c).sum()) for c in labels
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "confusion_matrix_labels": labels,
    }


def main() -> dict:
    train_df, test_df = load_raw("train"), load_raw("test")
    (Xtr_full, Xte_full), feat_names, _ = build_feature_matrix(train_df, test_df)

    labels = FAMILIES
    results = {"feature_count": len(feat_names), "model": "RandomForestClassifier(n_estimators=200)"}

    # ---------------- Protocol A: pooled random split (the common error) ----------------
    X_pool = pd.concat([Xtr_full, Xte_full], ignore_index=True)
    y_pool = pd.concat([train_df["family"], test_df["family"]], ignore_index=True)
    XA_tr, XA_te, yA_tr, yA_te = train_test_split(
        X_pool, y_pool, test_size=0.2, random_state=SEED, stratify=y_pool)

    t0 = time.time()
    mA = rf().fit(XA_tr, yA_tr)
    tA = time.time() - t0
    resA = score(yA_te, mA.predict(XA_te), labels)
    resA["train_seconds"] = round(tA, 2)
    resA["n_train"] = int(len(XA_tr))
    resA["n_test"] = int(len(XA_te))
    results["protocol_A_pooled_random_split"] = resA

    # ---------------- Protocol B: official split (honest) ----------------
    t0 = time.time()
    mB = rf().fit(Xtr_full, train_df["family"])
    tB = time.time() - t0
    predB = mB.predict(Xte_full)
    resB = score(test_df["family"], predB, labels)
    resB["train_seconds"] = round(tB, 2)
    resB["n_train"] = int(len(Xtr_full))
    resB["n_test"] = int(len(Xte_full))
    results["protocol_B_official_split"] = resB

    # ---------------- The gap ----------------
    results["gap"] = {
        "accuracy_points": round(
            (resA["accuracy"] - resB["accuracy"]) * 100, 2),
        "macro_f1_points": round(
            (resA["macro_f1"] - resB["macro_f1"]) * 100, 2),
        "relative_error_increase_x": round(
            (1 - resB["accuracy"]) / max(1e-9, (1 - resA["accuracy"])), 1),
    }

    # ---------------- Where the honest model actually fails ----------------
    te = test_df.copy()
    te["pred"] = predB
    te["correct_family"] = (te["pred"] == te["family"]).astype(int)
    # An attack called "Normal" is the operationally catastrophic error.
    te["missed_as_normal"] = ((te["is_attack"] == 1) & (te["pred"] == "Normal")).astype(int)

    results["failure_analysis"] = {
        "seen_attacks": {
            "n": int(((te.is_attack == 1) & (te.is_novel == 0)).sum()),
            "family_accuracy": round(float(
                te.loc[(te.is_attack == 1) & (te.is_novel == 0), "correct_family"].mean()), 4),
            "missed_as_normal_rate": round(float(
                te.loc[(te.is_attack == 1) & (te.is_novel == 0), "missed_as_normal"].mean()), 4),
        },
        "novel_attacks": {
            "n": int((te.is_novel == 1).sum()),
            "family_accuracy": round(float(te.loc[te.is_novel == 1, "correct_family"].mean()), 4),
            "missed_as_normal_rate": round(float(
                te.loc[te.is_novel == 1, "missed_as_normal"].mean()), 4),
        },
        "per_novel_attack_type": {
            str(k): {
                "n": int(v["is_novel"].size),
                "detected_as_attack_rate": round(float(1 - v["missed_as_normal"].mean()), 4),
                "correct_family_rate": round(float(v["correct_family"].mean()), 4),
            }
            for k, v in te[te.is_novel == 1].groupby("label")[
                ["is_novel", "missed_as_normal", "correct_family"]]
        },
    }

    # Binary attack/normal view — what a real IDS alarm would do.
    yb_true = test_df["is_attack"].values
    yb_pred = (predB != "Normal").astype(int)
    tn, fp, fn, tp = confusion_matrix(yb_true, yb_pred, labels=[0, 1]).ravel()
    results["binary_detection_official_split"] = {
        "true_negative": int(tn), "false_positive": int(fp),
        "false_negative": int(fn), "true_positive": int(tp),
        "detection_rate_recall": round(float(tp / (tp + fn)), 4),
        "false_alarm_rate": round(float(fp / (fp + tn)), 4),
        "precision": round(float(tp / (tp + fp)), 4),
    }

    out = METRICS / "leakage_experiment.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"[leakage] written -> {out}")
    return results


if __name__ == "__main__":
    r = main()
    A = r["protocol_A_pooled_random_split"]
    B = r["protocol_B_official_split"]
    print("\n" + "=" * 68)
    print("  PROTOCOL A (pooled random split — the common error)")
    print(f"    accuracy {A['accuracy']:.4f}   macro-F1 {A['macro_f1']:.4f}")
    print("  PROTOCOL B (official KDDTrain+ -> KDDTest+ — honest)")
    print(f"    accuracy {B['accuracy']:.4f}   macro-F1 {B['macro_f1']:.4f}")
    print("-" * 68)
    print(f"  GAP: {r['gap']['accuracy_points']} accuracy points, "
          f"{r['gap']['macro_f1_points']} macro-F1 points")
    print(f"  Error rate is {r['gap']['relative_error_increase_x']}x higher under honest eval")
    print("=" * 68)
    print("\n  Per-class recall (family):")
    for c in r["protocol_A_pooled_random_split"]["per_class_recall"]:
        a = A["per_class_recall"][c]; b = B["per_class_recall"][c]
        print(f"    {c:<7} A={a:.3f}   B={b:.3f}   (support in B: {B['per_class_support'][c]})")
    fa = r["failure_analysis"]
    print(f"\n  Seen attacks : family-acc {fa['seen_attacks']['family_accuracy']:.3f}, "
          f"missed-as-normal {fa['seen_attacks']['missed_as_normal_rate']:.3f}")
    print(f"  NOVEL attacks: family-acc {fa['novel_attacks']['family_accuracy']:.3f}, "
          f"missed-as-normal {fa['novel_attacks']['missed_as_normal_rate']:.3f}")
