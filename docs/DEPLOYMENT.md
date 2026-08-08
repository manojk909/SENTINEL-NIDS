# Deployment Considerations

Required by the TE-BE track. Written as what would actually have to be true to run this near a
network, including the parts we have *not* solved.

---

## 1. Measured performance characteristics

Benchmarked on the build container (2 vCPU x86_64, Python 3.11, ONNX Runtime single-threaded).
Source: `reports/metrics/deployment_benchmark.json`.

| Model | p50 / flow | p99 / flow | On-disk size | Throughput @ batch 4096 |
|---|---|---|---|---|
| **ONNX Runtime (logistic regression)** | **0.013 ms** | 0.045 ms | **4.9 KB** | **809,931 flows/s** |
| Decision tree | 0.079 ms | 0.183 ms | 51.8 KB | 5,072,935 flows/s |
| Logistic regression (sklearn) | 0.215 ms | 0.398 ms | 11.3 KB | 640,085 flows/s |
| MLP (128, 64) | 0.362 ms | 0.474 ms | 774.9 KB | 443,088 flows/s |
| XGBoost | 0.968 ms | 1.442 ms | 3.3 MB | 68,494 flows/s |
| LightGBM | 1.046 ms | 2.903 ms | 3.2 MB | 52,199 flows/s |
| Random forest (300 trees) | 65.206 ms | 85.493 ms | 38.4 MB | 31,428 flows/s |

### The deployment finding

**Random Forest — the default choice for this dataset in most published work and virtually every
tutorial — is 5,055× slower per flow and 8,027× larger on disk than logistic regression exported to
ONNX, while scoring 0.05 *lower* macro-F1 under honest evaluation.**

At 65 ms per flow on a per-request serving path, a single Random Forest worker sustains roughly 15
flows/second. That is not an intrusion detector; that is a bottleneck. The comparison is rarely
made because most ML-IDS papers report accuracy and stop.

Choosing the linear model is therefore not a compromise. It is simultaneously the better model on
the metric of record, the faster model, and the smaller model. The only thing it loses on is
in-distribution CV score — which is the number this project argues you should stop trusting.

### Capacity arithmetic (so the claim is checkable)

Classification is **per completed flow**, not per packet — NSL-KDD features are aggregates over a
finished connection. Taking a conservative 1 KiB mean flow size, a saturated 1 Gbps link produces
**122,070 flows/s**. Measured single-threaded throughput is **809,931 flows/s**, so one commodity
core covers a 1 Gbps link with **6.6× headroom**. Campus- or edge-scale deployment does
not need a GPU or a cluster.

**The honest caveat:** these numbers measure *model inference on pre-computed features*. Extracting
those 41 flow aggregates from a live packet stream — connection tracking, 2-second and
100-connection sliding windows, per-host state tables — is the harder engineering problem and is
**out of scope for this submission**. In any real deployment, feature extraction, not inference,
would be the binding cost. Most papers reporting "real-time ML-IDS" omit this.

---

## 2. Serving architecture

```
   packet capture ──► flow assembler ──► feature extractor ──► SENTINEL ──► verdict router
   (out of scope)     (out of scope)      (out of scope)       (this repo)
                                                                  │
                        ┌─────────────────────────────────────────┴────────────┐
                        │ Channel A: ONNX logistic regression   (4.9 KB)       │
                        │ Channel B: IsolationForest novelty    (normal-only)  │
                        │ alarm = A attack  OR  A abstains  OR  B outlier      │
                        └──────────────────────────────────────────────────────┘
                                                  │
              ┌───────────────────┬───────────────┴────────┬──────────────────────┐
         NORMAL              ATTACK:<family>     SUSPICIOUS_UNCLASSIFIED    (metrics)
         no action           priority alert       analyst triage queue      Prometheus
```

Reference implementation: [`../app/service.py`](../app/service.py) — FastAPI, models loaded once at
import (load is the expensive part, not inference), `/health`, `/predict`, `/predict_batch`.

**Three-way output is the core design decision.** A binary detector must either accuse or clear
every flow. Since we measured that a plain classifier clears 76.7% of unseen attacks as normal,
the third verdict is what converts a silent miss into a triaged alert. Every response also carries
the class probability vector, the confidence, whether the anomaly channel fired, and a
human-readable `reason` string — so an analyst is never handed a bare label.

**Unknown categorical values** (a `service` or `flag` never seen in training) encode to all-zeros
for that group rather than raising an error. That is the correct production behaviour, and it is
itself a weak novelty signal that Channel B tends to pick up.

---

## 3. Choosing the operating threshold τ

τ is **a staffing decision, not a hyperparameter.** It sets alert volume.

| τ | Unseen-attack detection | False-alarm rate | False alarms per 9,711 normal flows |
|---|---|---|---|
| 0.0 (no abstention) | 0.624 | 0.076 | 734 |
| 0.90 | 0.647 | 0.088 | 856 |
| **0.95 (recommended)** | **0.659** | **0.093** | **898** |
| 0.99 | 0.702 | 0.112 | 1,087 |
| 0.999 | 0.861 | 0.343 | 3,334 |

The recommended point is defined by a stated rule — maximise unseen-attack detection subject to
false-alarm rate ≤ 10% — not chosen by eye. Full curve: `reports/metrics/zeroday_experiment.json`.

`app/service.py` **reads τ from that JSON at import** rather than hardcoding it, so the served
threshold and the reported threshold cannot drift apart.

Note the shape of the curve: pushing from τ=0.95 to τ=0.999 buys +20 points of unseen-attack
coverage for **+25 points** of false alarms. Whether that trade is right depends entirely on
whether the environment is a student lab or a defence network. We refuse to decide it for the
operator.

---

## 4. Drift monitoring and retraining

The whole project is an argument that this model's performance depends on the traffic distribution
matching training. So monitoring drift is not optional infrastructure — it is the primary safety
mechanism.

### Signals to monitor continuously

| Signal | Why | Trigger |
|---|---|---|
| **Rate of `SUSPICIOUS_UNCLASSIFIED`** | The cheapest available novelty alarm. A sustained rise means traffic is moving away from training. | > 2× the 7-day trailing baseline |
| **Channel B outlier rate** | Independent of Channel A; rises when flows are unlike *normal* training traffic. | > 1.5× baseline over 24 h |
| **Mean Channel A confidence** | Falling confidence precedes accuracy loss and needs no labels. | 7-day mean drops > 0.05 |
| **Unknown categorical-value rate** | New services/protocols on the network — direct evidence of environment change. | any sustained non-zero rate |
| **Per-feature PSI / KS vs training** | Locates *which* feature moved, which tells you what changed. | PSI > 0.2 on any top-20 feature |
| Confirmed-detection precision | The only true-performance signal, but requires analyst labels. | precision drop > 10% |

### Retraining policy

1. **Scheduled:** quarterly on freshly captured, analyst-labelled traffic.
2. **Triggered:** any drift signal above threshold for 48 h.
3. **Mandatory:** on any environment change — new subnet, new application tier, protocol migration.

**Retraining must preserve the honest evaluation protocol.** Hold out entire attack families and
entire time periods, never random rows. If you random-split the retraining data, every metric you
produce becomes uninterpretable — that is the finding of this project, and it applies to future-you
as much as to the literature.

Keep the previous model artefact and its metrics; a new model ships only if it beats the incumbent
on **macro-F1 and unseen-attack detection**, not on accuracy.

---

## 5. Failure modes

| Failure mode | Consequence | Mitigation in this design | Residual risk |
|---|---|---|---|
| **Unseen attack family** | Silent miss | Channel B + abstention; raises coverage 41.5% → 65.9% | **34% still missed.** Real and unresolved. |
| **R2L / U2R attack** | Compromise undetected | None effective | Recall 0.11 / 0.08. The model should not be relied on here at all. |
| **Alert fatigue** | Team stops reading alerts; effective detection → 0 | τ exposed as an explicit dial; false-alarm rate reported at every operating point | Human factor, outside the model |
| **Adversarial evasion** | Attacker shapes traffic to look normal | **Not addressed.** A linear model is especially easy to evade under white-box knowledge. | High. Requires adversarial training; out of scope. |
| **Feature-extractor drift** | Silently wrong inputs; model appears fine | Unknown-value rate is monitored | Extractor is out of scope here |
| **Encrypted traffic** | Content features unavailable | None | Content features are only 1.2% of importance, so degradation is smaller than expected — but R2L/U2R detection, which needs them, degrades further |
| **Model file tampering** | Compromised verdicts | Not addressed | Sign artefacts and verify at load in any real deployment |

### The most important row

**Adversarial evasion is not addressed at all.** An intrusion detector faces an adaptive adversary,
and we evaluate against a fixed 1999 dataset. Nothing in these results speaks to robustness against
someone who knows the model. Stating this is more useful than a caveat-free claim.

---

## 6. What would be needed before going anywhere near a real network

1. Retrain on traffic captured from that specific environment.
2. Build and validate the feature extractor (the actual hard part).
3. Adversarial robustness evaluation.
4. Shadow-mode deployment: run alongside the existing IDS for ≥ 1 month, compare alerts, tune τ
   against real analyst capacity.
5. Signed model artefacts and verification at load.
6. A rollback path to the previous model, tested.
7. Resolve — or explicitly accept — the R2L/U2R blind spot.

Items 1–3 are each larger than this entire submission. That is the honest scope statement.
