# SENTINEL-NIDS — Problem Statement

**ML Bubble 2026 · Track: TE-BE (Design & Solve — Advanced)**
**Domain: Defense & National Security × Cybersecurity × Predictive Analytics**
**Participant: Manoj Kharkar (solo)**
**Locked: 08 Aug 2026, 11:00 AM IST**

---

## 1. The real-world problem

Critical national infrastructure — defence networks, power grids, military logistics systems —
is defended largely by **signature-based intrusion detection**: a system flags traffic only if it
matches a known attack pattern. This is structurally blind to any attack that has not been seen
before. Machine learning is the obvious replacement, and the published literature enthusiastically
reports **97–99% accuracy** on benchmark intrusion datasets.

**Those numbers are, in a strict sense, a lie — and deploying a model built on them would leave a
network defenceless against exactly the attacks that matter most.**

This project's purpose is to demonstrate that claim empirically, quantify the damage, and then
build an intrusion detector that is evaluated honestly.

## 2. Why this is an ML problem (and a hard one)

Intrusion detection is not a pattern-matching problem, it is a **distribution-shift** problem:

- The attacker is adversarial and *actively* invents traffic the model has never seen.
- Attack classes are severely imbalanced — the most dangerous categories are the rarest.
- The cost of a false negative (missed intrusion on a defence network) is not symmetric with a
  false positive (an analyst wastes five minutes).
- Deployment is latency-bound: detection must happen at line rate, per flow, in milliseconds.

Standard supervised ML assumes train and test are drawn from the same distribution. In intrusion
detection that assumption is false by definition. That is the crux.

## 3. The central hypothesis

> The high accuracies reported for ML-based intrusion detection are an artefact of **evaluating on
> a random split of a single dataset**. Under a realistic protocol — where the test set contains
> attack types absent from training — performance collapses, and the collapse is concentrated
> precisely in the rarest and most severe attack categories.

## 4. Dataset and why it can prove the hypothesis

**NSL-KDD** (Tavallaee et al., 2009), the de-duplicated revision of KDD Cup '99.
Retrieved from a public GitHub mirror (see `data/README.md` for provenance).

| Property | Value (verified in this repo) |
|---|---|
| Train records (`KDDTrain+`) | 125,973 |
| Test records (`KDDTest+`) | 22,544 |
| Features | 41 (+ label, + difficulty) |
| Exact duplicate rows in train | 0 (this is the NSL fix over KDD'99) |
| Distinct attack types in train | 22 |
| Distinct attack types in test | 37 |
| **Attack types present ONLY in test** | **17** |

The 17 unseen attack types are:
`apache2, httptunnel, mailbomb, mscan, named, processtable, ps, saint, sendmail, snmpgetattack,
snmpguess, sqlattack, udpstorm, worm, xlock, xsnoop, xterm`

**This is the key property.** NSL-KDD ships with a *designed* train/test distribution shift: the
official test set is a built-in zero-day benchmark. Almost every tutorial and a great deal of
published work discards this by concatenating train+test and re-splitting at random — which is
exactly the methodological error this project isolates and measures.

### Why not a "fresher" dataset
UNSW-NB15, CIC-IDS2017 and HuggingFace-hosted NIDS corpora were all attempted; their hosts are
unreachable from the build environment (verified — see `docs/METHODOLOGY.md`). NSL-KDD is
additionally the *right* choice here on merit: it is the only widely-used benchmark with a
documented, citable unseen-attack test protocol, it is small enough to permit genuine
cross-validated comparison of many models within the round's time budget, and it is tabular —
which makes per-feature attribution possible. That last point matters directly, because
**Round 2 is a "Model Explanation Round"**: a model whose decisions can be attributed to named
network features is defensible under questioning in a way a deep sequence model is not.

Its age (1999-era traffic) is a genuine limitation and is stated plainly in
`docs/MODEL_CARD.md` rather than hidden.

## 5. What will be built

1. **The leakage experiment (headline).** Train one identical model under two protocols —
   (A) random 80/20 split of pooled train+test, (B) the official `KDDTrain+` → `KDDTest+` split.
   Report both. The gap is the finding.
2. **Comparative analysis** of 6 models (majority baseline, Logistic Regression, Random Forest,
   XGBoost, LightGBM, MLP) on *identical* splits, scored with macro-F1 and per-class recall
   rather than accuracy — because a detector that ignores the two rarest attack classes entirely
   can still reach 86.9% accuracy — R2L and U2R are only 13.1% of the test set.
3. **Zero-day evaluation.** Leave-one-attack-family-out protocol, plus a novelty-detection layer
   that flags traffic as "anomalous but unclassifiable" instead of silently mislabelling an unseen
   attack as normal.
4. **Explainability.** SHAP + permutation importance per attack family.
5. **Deployment considerations.** ONNX export, measured per-flow latency and throughput, a minimal
   inference service, and a monitoring/retraining plan keyed to detected drift.

## 6. Success criteria for this submission

| # | Criterion | Target |
|---|---|---|
| 1 | Leakage gap quantified and reproducible | Both numbers reported, single command |
| 2 | Honest macro-F1 on official test split | Reported without cherry-picking |
| 3 | Per-class recall on rare classes (R2L, U2R) | Reported even where it is poor |
| 4 | Models compared on identical splits | ≥5 models + baseline |
| 5 | Unseen-attack detection rate | Measured on the 17 novel types |
| 6 | Inference latency | Measured, in ms/flow |
| 7 | Clean-clone reproducibility | `pip install -r requirements.txt && python run_all.py` |

## 7. Honest framing (deliberate)

This project does **not** claim a state-of-the-art detector. It claims that the field's reported
numbers are inflated by a specific, identifiable evaluation error, demonstrates that with a
controlled experiment, and delivers a detector whose real-world performance is stated accurately
including where it fails. For a defence-affiliated evaluator, a system whose limits are known is
worth more than one whose headline number cannot be trusted.
