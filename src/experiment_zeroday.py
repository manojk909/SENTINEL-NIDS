"""Zero-day / unseen-attack evaluation — and the proposed fix.

Part 1 — LOFO (Leave-One-Family-Out).
    For each attack family F, train a detector on Normal + every attack family EXCEPT F,
    then measure how often it flags F. From the model's point of view F is a zero-day.
    This is the controlled version of what KDDTest+ does by design.

Part 2 — The abstention + anomaly hybrid (SENTINEL's actual proposal).
    Diagnosis from experiment_leakage.py: 76.7% of unseen attacks are labelled "Normal",
    i.e. they raise no alarm. The cause is structural — a softmax over 5 known classes has
    no way to say "this is none of these". So we add two channels:

      Channel A (supervised, with abstention): if max class probability < tau, do not emit
          "Normal"; emit SUSPICIOUS_UNCLASSIFIED and route to an analyst.
      Channel B (unsupervised novelty): IsolationForest fitted on NORMAL TRAFFIC ONLY.
          It never sees an attack in training, so it cannot be biased toward known ones.

    Final alarm = (supervised says attack) OR (supervised abstains) OR (channel B says outlier).

    Reported as an operating curve: unseen-attack coverage gained vs false-alarm cost paid.
    A security operations centre picks the point; we do not pick it for them.

Crash-safe: each part writes its own checkpoint under reports/metrics/ as soon as it finishes.

Writes reports/metrics/zeroday_experiment.json (+ zeroday_lofo.json partial)
"""
from __future__ import annotations

import json
import time

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import METRICS, MODELS, SEED
from data import build_feature_matrix, load_raw

ATTACK_FAMILIES = ["DoS", "Probe", "R2L", "U2R"]


# ----------------------------------------------------------------- Part 1
def lofo(train_df, test_df, Xtr, Xte) -> dict:
    """Leave-One-Family-Out: each family held out entirely, then tested as a zero-day."""
    ck = METRICS / "zeroday_lofo.json"
    if ck.exists():
        print("[lofo] cached -> skipping")
        return json.loads(ck.read_text())

    y_all = (train_df["family"] != "Normal").astype(int)

    # Reference model (family present) is fitted once and reused.
    print("[lofo] fitting reference model (all families present) ...", flush=True)
    clf_full = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=SEED)
    clf_full.fit(Xtr, y_all)
    pred_full = clf_full.predict(Xte)

    out = {}
    for fam in ATTACK_FAMILIES:
        keep = (train_df["family"] != fam).values
        clf = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=SEED)
        t0 = time.time()
        clf.fit(Xtr[keep], y_all[keep])
        fit_s = time.time() - t0

        mask_fam = (test_df["family"] == fam).values
        mask_norm = (test_df["family"] == "Normal").values
        pred = clf.predict(Xte)

        det = float(pred[mask_fam].mean()) if mask_fam.sum() else float("nan")
        det_full = float(pred_full[mask_fam].mean()) if mask_fam.sum() else float("nan")

        out[fam] = {
            "train_rows_removed": int((~keep).sum()),
            "test_rows_of_family": int(mask_fam.sum()),
            "detection_rate_family_HELD_OUT": round(det, 4),
            "detection_rate_family_INCLUDED": round(det_full, 4),
            "detection_loss": round(det_full - det, 4),
            "false_alarm_rate_on_normal": round(float(pred[mask_norm].mean()), 4),
            "fit_seconds": round(fit_s, 1),
        }
        print(f"[lofo] {fam:<6} held-out {det:.3f}  vs included {det_full:.3f}"
              f"  (loss {det_full - det:+.3f})", flush=True)
        ck.write_text(json.dumps(out, indent=2))  # checkpoint after every family
    return out


# ----------------------------------------------------------------- Part 2
def hybrid(train_df, test_df, Xtr, Xte) -> dict:
    """Abstention + unsupervised novelty channel, swept as an operating curve."""
    ytr = train_df["family"].values

    # Channel A — LogisticRegression: it was the strongest generaliser under shift in
    # model_comparison.json, and its probabilities are better behaved than a forest's
    # vote share for thresholding.
    print("[hybrid] fitting supervised channel ...", flush=True)
    supervised = Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, n_jobs=-1, random_state=SEED)),
    ])
    supervised.fit(Xtr, ytr)
    proba = supervised.predict_proba(Xte)
    classes = np.array(supervised.named_steps["clf"].classes_)
    pred_lbl = classes[proba.argmax(axis=1)]
    conf = proba.max(axis=1)

    # Channel B — novelty, fitted on NORMAL rows only.
    normal_only = Xtr[(train_df["family"] == "Normal").values]
    print(f"[hybrid] fitting IsolationForest on {len(normal_only):,} normal flows ...",
          flush=True)
    iso = Pipeline([
        ("scale", StandardScaler()),
        ("iso", IsolationForest(n_estimators=300, contamination=0.02,
                                random_state=SEED, n_jobs=-1)),
    ])
    iso.fit(normal_only)
    iso_outlier = (iso.predict(Xte) == -1)

    joblib.dump(supervised, MODELS / "hybrid_supervised_logreg.joblib")
    joblib.dump(iso, MODELS / "hybrid_novelty_isoforest.joblib")

    is_attack = test_df["is_attack"].values.astype(bool)
    is_novel = test_df["is_novel"].values.astype(bool)
    is_seen = is_attack & ~is_novel
    is_normal = ~is_attack

    def measure(alarm) -> dict:
        return {
            "overall_detection_rate": round(float(alarm[is_attack].mean()), 4),
            "seen_attack_detection_rate": round(float(alarm[is_seen].mean()), 4),
            "novel_attack_detection_rate": round(float(alarm[is_novel].mean()), 4),
            "false_alarm_rate": round(float(alarm[is_normal].mean()), 4),
            "novel_missed": int((~alarm[is_novel]).sum()),
            "false_alarms": int(alarm[is_normal].sum()),
        }

    res = {
        "supervised_model": "StandardScaler + LogisticRegression(max_iter=1000)",
        "novelty_model": "StandardScaler + IsolationForest(n_estimators=300, "
                         "contamination=0.02) fitted on NORMAL traffic only",
        "n_normal_train_rows_for_novelty": int(len(normal_only)),
    }

    base_alarm = (pred_lbl != "Normal")
    res["channel_A_only_no_abstention"] = measure(base_alarm)
    res["channel_B_only_isolationforest"] = measure(iso_outlier)
    res["channel_A_or_B_no_abstention"] = measure(base_alarm | iso_outlier)

    curve = []
    for tau in [0.0, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.999]:
        abstain = (pred_lbl == "Normal") & (conf < tau)
        alarm_sup = base_alarm | abstain
        row = {"tau": tau,
               "abstained_flows": int(abstain.sum()),
               "A_with_abstention": measure(alarm_sup),
               "A_with_abstention_OR_B": measure(alarm_sup | iso_outlier)}
        curve.append(row)
        m = row["A_with_abstention_OR_B"]
        print(f"[hybrid] tau={tau:<6} novel-det {m['novel_attack_detection_rate']:.3f}  "
              f"overall-det {m['overall_detection_rate']:.3f}  "
              f"FAR {m['false_alarm_rate']:.3f}", flush=True)
    res["operating_curve"] = curve

    # Recommended point: best unseen-attack coverage subject to FAR <= 10%.
    feasible = [(r["tau"], r["A_with_abstention_OR_B"]) for r in curve
                if r["A_with_abstention_OR_B"]["false_alarm_rate"] <= 0.10]
    if feasible:
        tau_star, m_star = max(feasible,
                               key=lambda t: t[1]["novel_attack_detection_rate"])
        res["recommended_operating_point"] = {
            "constraint": "false_alarm_rate <= 0.10", "tau": tau_star, **m_star}
        base = res["channel_A_only_no_abstention"]
        res["improvement_vs_plain_classifier"] = {
            "novel_detection_before": base["novel_attack_detection_rate"],
            "novel_detection_after": m_star["novel_attack_detection_rate"],
            "novel_detection_gain_pp": round(
                (m_star["novel_attack_detection_rate"]
                 - base["novel_attack_detection_rate"]) * 100, 2),
            "false_alarm_before": base["false_alarm_rate"],
            "false_alarm_after": m_star["false_alarm_rate"],
            "false_alarm_cost_pp": round(
                (m_star["false_alarm_rate"] - base["false_alarm_rate"]) * 100, 2),
        }
    return res


def main() -> dict:
    train_df, test_df = load_raw("train"), load_raw("test")
    (Xtr, Xte), feat_names, _ = build_feature_matrix(train_df, test_df)
    Xtr, Xte = Xtr.values, Xte.values  # numpy: boolean row masks below

    res = {"n_features": len(feat_names)}
    print("\n=== Part 1: Leave-One-Family-Out ===", flush=True)
    res["lofo"] = lofo(train_df, test_df, Xtr, Xte)
    (METRICS / "zeroday_experiment.json").write_text(json.dumps(res, indent=2))

    print("\n=== Part 2: Abstention + novelty hybrid ===", flush=True)
    res["hybrid"] = hybrid(train_df, test_df, Xtr, Xte)
    (METRICS / "zeroday_experiment.json").write_text(json.dumps(res, indent=2))
    print(f"\n[zeroday] written -> {METRICS / 'zeroday_experiment.json'}")
    return res


if __name__ == "__main__":
    r = main()
    imp = r["hybrid"].get("improvement_vs_plain_classifier")
    if imp:
        print("\n" + "=" * 70)
        print("  UNSEEN-ATTACK DETECTION")
        print(f"    plain 5-class classifier : {imp['novel_detection_before']*100:5.1f}%")
        print(f"    SENTINEL hybrid          : {imp['novel_detection_after']*100:5.1f}%"
              f"   (+{imp['novel_detection_gain_pp']} pp)")
        print(f"    false-alarm cost         : {imp['false_alarm_before']*100:.1f}%"
              f" -> {imp['false_alarm_after']*100:.1f}%"
              f"  (+{imp['false_alarm_cost_pp']} pp)")
        print("=" * 70)
