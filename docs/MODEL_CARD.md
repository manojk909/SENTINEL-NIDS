# Model Card — SENTINEL-NIDS

Following the model-card convention of Mitchell et al. (2019). Written to be read by someone
deciding whether to trust this system, not to market it.

---

## Model details

| | |
|---|---|
| **Name** | SENTINEL-NIDS v1.0 |
| **Date** | 08 August 2026 |
| **Author** | Manoj Kharkar (solo) — ML Bubble 2026, TE-BE Advanced track |
| **Type** | Two-channel network intrusion detector with explicit abstention |
| **Channel A** | `StandardScaler` → `LogisticRegression(max_iter=1000)`, 5-class |
| **Channel B** | `StandardScaler` → `IsolationForest(n_estimators=300, contamination=0.02)`, fitted on normal traffic only |
| **Input** | 41 NSL-KDD flow features → 122 after one-hot encoding (train vocabulary only) |
| **Output** | One of `NORMAL`, `ATTACK:{DoS,Probe,R2L,U2R}`, `SUSPICIOUS_UNCLASSIFIED`, plus class probabilities, confidence, and a reason string |
| **Decision rule** | `alarm = A says attack OR A abstains (conf < τ) OR B says outlier`; τ = 0.95 |
| **Served artefact** | `models/sentinel_best.onnx` — 4.9 KB, 0.013 ms/flow p50 |
| **Licence** | Academic/non-commercial, consistent with the NSL-KDD terms |

---

## Intended use

**Intended.** An educational and research demonstration of (a) how evaluation protocol choice
inflates reported intrusion-detection performance, and (b) how abstention plus an unsupervised
novelty channel partially mitigates blindness to unseen attacks. Suitable as a teaching artefact,
a baseline for further research, and a template for honest ML evaluation reporting.

**Intended users.** Students, researchers, and engineers evaluating ML-IDS claims critically.

### Out of scope — do NOT use this for

- **Protecting a real network.** It is trained on 1999 simulated traffic. It has never seen TLS 1.3,
  QUIC, HTTP/2, containerised east-west traffic, cloud metadata services, or any attack tooling from
  the last two decades.
- **Any automated blocking or enforcement action.** At the recommended operating point it flags
  9.25% of normal traffic. Automated blocking would take a functioning network down.
- **Detecting privilege escalation or remote-to-local intrusion.** Best-case recall across all eight models is 0.105 for U2R
  and 0.106 for R2L. It is close to useless for the two families that indicate actual compromise, and we
  say so.
- **Any claim that ML-IDS "achieves 99% accuracy."** The entire point of this repository is that
  such claims are protocol artefacts.

---

## Performance

All figures on the official `KDDTest+` split (22,544 flows), which contains 17 attack types absent
from training.

### The two-channel detector (recommended operating point, τ = 0.95)

| Metric | Value |
|---|---|
| Overall attack detection rate | 0.762 |
| Seen-attack-type detection | 0.805 |
| **Unseen-attack-type detection** | **0.659** |
| False-alarm rate on normal traffic | 0.093 |

### Ablation

| Configuration | Unseen detection | Seen detection | False-alarm rate |
|---|---|---|---|
| Channel A alone (plain 5-class classifier) | 0.415 | 0.756 | 0.070 |
| Channel B alone (trained on zero attacks) | 0.566 | 0.638 | 0.020 |
| A OR B, no abstention | 0.624 | 0.770 | 0.076 |
| **A + abstention (τ=0.95) OR B** | **0.659** | 0.805 | 0.093 |
| A + abstention (τ=0.999) OR B | 0.861 | 0.977 | 0.343 |

### Underlying 5-class classifier performance (for context)

Best single model was an MLP (128, 64) at macro-F1 **0.5460**, accuracy 0.7812. Per-class recall for
the Random Forest reference model under the honest protocol:

| Family | Recall | Test support |
|---|---|---|
| Normal | 0.974 | 9,711 |
| DoS | 0.797 | 7,458 |
| Probe | 0.603 | 2,421 |
| R2L | 0.038 | 2,754 |
| U2R | 0.005 | 200 |

**Under the pooled-random-split protocol the same model reports accuracy 0.9951 and macro-F1
0.9548.** That number is included only to demonstrate that it is meaningless.

### Deployment characteristics

| | p50 latency | p99 | Size | Throughput |
|---|---|---|---|---|
| ONNX Runtime, single-threaded | 0.013 ms/flow | 0.045 ms | 4.9 KB | 809,931 flows/s (batch 4096) |

Measured on a 2 vCPU x86_64 container. Absolute values are hardware-dependent; ratios between
models transfer.

---

## Training data

**NSL-KDD** (Tavallaee et al., IEEE CISDA 2009), the de-duplicated revision of KDD Cup 1999.
`KDDTrain+`: 125,973 flows. Full provenance, schema, licence and limitations in
[`../data/README.md`](../data/README.md).

Class distribution in training: Normal 53.5%, DoS 36.5%, Probe 9.3%, **R2L 0.79%, U2R 0.04%**.

**The training data is a simulation.** The underlying DARPA 1998/1999 traffic was synthetically
generated with injected attacks; base rates reflect no real network. This is the single most
important limitation of the model.

---

## Evaluation data

`KDDTest+`: 22,544 flows, **deliberately not drawn from the training distribution**:

- 17 of 37 attack types occur only here (3,750 flows, 16.6%)
- R2L is 15.5× and U2R 21.5× more frequent than in training

No hyperparameter was tuned against this split.

---

## Ethical considerations

- **False positives have human cost.** A 9.25% false-alarm rate means a large alert queue. Deployed
  naively this produces alert fatigue, which makes a security team *less* effective, not more.
- **Automation bias.** A verdict of `SUSPICIOUS_UNCLASSIFIED` is an instruction to investigate, not
  a finding. The three-way output exists specifically so the system cannot silently assert safety.
- **Dual use is limited but real.** The per-attack-type detection table shows which attack families
  evade detection. Published on a 27-year-old benchmark against no live system, the disclosure value
  to defenders substantially exceeds any offensive value.
- **No personal data.** NSL-KDD contains synthetic flow aggregates, no payloads, no identifiers.

---

## Caveats and recommendations

1. **Never deploy this on a live network.** Retrain on traffic captured from the actual environment,
   validated with the same honest protocol used here.
2. **Preserve the evaluation protocol when retraining.** Hold out entire attack families, not
   random rows. The moment you random-split, your metrics stop meaning anything — that is the
   finding of this project.
3. **Treat τ as a staffing decision.** It sets the alert volume. Pick it from the operating curve in
   `reports/metrics/zeroday_experiment.json` against the queue your team can actually service.
4. **Monitor for drift and expect to retrain.** See [`DEPLOYMENT.md`](DEPLOYMENT.md).
5. **The unresolved problem is R2L/U2R.** Content-based features (failed logins, shell access, file
   creation) carry that signal and are the place to invest. Anyone extending this work should start
   there.

---

## Reproduce these numbers

```bash
pip install -r requirements.txt
python run_all.py
```

Everything in this card is generated into `reports/metrics/*.json`. No figure here was typed by
hand.
