"""SENTINEL-NIDS inference service.

A minimal, honest serving path for the two-channel detector. Deliberately small: the point
is to show the deployment shape (load once, validate input, score, return a decision plus a
reason), not to ship a product.

Run:
    pip install fastapi uvicorn
    uvicorn app.service:app --host 127.0.0.1 --port 8000

Then:
    curl -s localhost:8000/health
    curl -s -X POST localhost:8000/predict -H 'content-type: application/json' \
         -d @app/example_request.json

Design decisions worth defending in a viva:

  * The service returns THREE possible verdicts, not two: NORMAL, ATTACK:<family>, and
    SUSPICIOUS_UNCLASSIFIED. The third exists because the model provably cannot recognise
    attack types absent from training (76.7% of unseen attacks were labelled "normal" by a
    plain classifier). Abstention converts a silent miss into a triaged alert.
  * Confidence is returned alongside every verdict, so a downstream SOC can route by it.
  * The anomaly channel is queried on every request, not only on low confidence — it is
    cheap and it catches flows the supervised model is confidently wrong about.
  * Unknown categorical values (a service or flag never seen in training) encode to
    all-zeros for that group rather than raising. That is the correct production behaviour
    and is itself a weak novelty signal, which the anomaly channel then picks up.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

# ---- loaded once at import: model load is the expensive part, not inference ----
_meta = joblib.load(MODELS / "preprocessor_meta.joblib")
FEATURES: List[str] = _meta["feature_names"]
VOCAB: Dict[str, List[str]] = _meta["vocab"]
CATEGORICAL = list(VOCAB.keys())

_supervised = joblib.load(MODELS / "hybrid_supervised_logreg.joblib")
_novelty = joblib.load(MODELS / "hybrid_novelty_isoforest.joblib")

# Operating threshold. Sourced from reports/metrics/zeroday_experiment.json
# ("recommended_operating_point"), i.e. chosen by measurement, not by feel.
_zd = ROOT / "reports" / "metrics" / "zeroday_experiment.json"
TAU = 0.99
if _zd.exists():
    try:
        TAU = json.loads(_zd.read_text())["hybrid"]["recommended_operating_point"]["tau"]
    except Exception:
        pass

NUMERIC = [f for f in FEATURES if "__" not in f]


def encode(flow: Dict[str, Any]) -> np.ndarray:
    """Build one feature row using the TRAINING vocabulary only.

    Missing numeric fields default to 0. Unseen categorical values produce an all-zero
    one-hot group — see the module docstring for why that is deliberate.
    """
    row = np.zeros(len(FEATURES), dtype=np.float32)
    pos = {f: i for i, f in enumerate(FEATURES)}
    for f in NUMERIC:
        v = flow.get(f, 0)
        try:
            row[pos[f]] = float(v)
        except (TypeError, ValueError):
            row[pos[f]] = 0.0
    unknown = []
    for c in CATEGORICAL:
        v = flow.get(c)
        key = f"{c}__{v}"
        if key in pos:
            row[pos[key]] = 1.0
        elif v is not None:
            unknown.append({c: v})
    return row.reshape(1, -1), unknown


def classify(flow: Dict[str, Any]) -> Dict[str, Any]:
    X, unknown = encode(flow)

    proba = _supervised.predict_proba(X)[0]
    classes = list(_supervised.named_steps["clf"].classes_)
    k = int(np.argmax(proba))
    label, conf = classes[k], float(proba[k])
    anomalous = bool(_novelty.predict(X)[0] == -1)

    if label != "Normal":
        verdict, reason = f"ATTACK:{label}", "supervised classifier identified a known family"
    elif anomalous:
        verdict, reason = ("SUSPICIOUS_UNCLASSIFIED",
                           "classifier said normal, but the anomaly channel (trained only "
                           "on normal traffic) flagged this flow as an outlier")
    elif conf < TAU:
        verdict, reason = ("SUSPICIOUS_UNCLASSIFIED",
                           f"classifier said normal but with confidence {conf:.3f} < "
                           f"tau={TAU}; abstaining rather than clearing the flow")
    else:
        verdict, reason = "NORMAL", "high-confidence normal, anomaly channel agrees"

    return {
        "verdict": verdict,
        "reason": reason,
        "supervised_label": label,
        "confidence": round(conf, 4),
        "class_probabilities": {c: round(float(p), 4) for c, p in zip(classes, proba)},
        "anomaly_channel_flagged": anomalous,
        "abstention_threshold_tau": TAU,
        "unknown_categorical_values": unknown,
    }


# --------------------------------------------------------------------- HTTP layer
try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field

    class Flow(BaseModel):
        """A completed network flow described by NSL-KDD features. All fields optional;
        omitted numerics default to 0, which mirrors how a real collector emits sparse
        records."""
        model_config = {"extra": "allow"}
        duration: Optional[float] = Field(default=0)
        protocol_type: Optional[str] = Field(default=None)
        service: Optional[str] = Field(default=None)
        flag: Optional[str] = Field(default=None)
        src_bytes: Optional[float] = Field(default=0)
        dst_bytes: Optional[float] = Field(default=0)

    app = FastAPI(
        title="SENTINEL-NIDS",
        version="1.0",
        description="Two-channel network intrusion detection with explicit abstention. "
                    "Returns NORMAL, ATTACK:<family>, or SUSPICIOUS_UNCLASSIFIED.")

    @app.get("/health")
    def health():
        return {"status": "ok", "n_features": len(FEATURES),
                "abstention_threshold_tau": TAU,
                "channels": ["supervised_logreg", "isolationforest_novelty"]}

    @app.post("/predict")
    def predict(flow: Flow):
        return classify(flow.model_dump())

    @app.post("/predict_batch")
    def predict_batch(flows: List[Flow]):
        return [classify(f.model_dump()) for f in flows]

except ImportError:  # FastAPI absent -> module still importable for CLI use
    app = None


if __name__ == "__main__":
    # CLI smoke test with no HTTP dependency: replay a few real test flows.
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from data import load_raw  # noqa: E402

    te = load_raw("test")
    print(f"loaded {len(te):,} test flows; tau={TAU}\n")

    # Deliberately includes cases the system gets RIGHT and cases it gets WRONG.
    # snmpguess and worm are R2L, the family with 0.038 recall — they are shown because
    # hiding the failure would misrepresent the system. See docs/MODEL_CARD.md.
    demo = [
        ("normal",       "benign traffic"),
        ("neptune",      "known DoS (SYN flood) — in training set"),
        ("saint",        "UNSEEN Probe — caught (98.4% detection for this type)"),
        ("apache2",      "UNSEEN DoS — caught about half the time (46.7%)"),
        ("snmpguess",    "UNSEEN R2L — MISSED (0% detection: the known blind spot)"),
        ("worm",         "UNSEEN R2L — MISSED (0% detection: the known blind spot)"),
    ]
    caught = missed = 0
    for lbl, note in demo:
        sub = te[te["label"] == lbl]
        if not len(sub):
            continue
        row = sub.iloc[0]
        r = classify(row.to_dict())
        is_atk = bool(row["is_attack"])
        alarmed = r["verdict"] != "NORMAL"
        ok = alarmed == is_atk
        if is_atk:
            caught += int(alarmed)
            missed += int(not alarmed)
        print(f"{'PASS' if ok else 'FAIL'}  {lbl:<14} {note}")
        print(f"        true={row['family']:<7} novel={bool(row['is_novel'])}")
        print(f"     -> {r['verdict']}  (conf {r['confidence']}, "
              f"anomaly={r['anomaly_channel_flagged']})")
        print(f"        {r['reason']}\n")
    print(f"of the attack samples shown: {caught} alarmed, {missed} silently cleared.")
    print("The misses are real and expected — see docs/MODEL_CARD.md 'Out of scope'.")
