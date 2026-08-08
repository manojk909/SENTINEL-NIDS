# Methodology

Every design decision in SENTINEL-NIDS, and why it was made that way. Written so that a reviewer
can attack any individual choice without having to reverse-engineer it from code.

---

## 1. Problem formulation

**Task.** Given the 41 flow-level features of a completed network connection, assign it to one of
five classes: `Normal`, `DoS`, `Probe`, `R2L`, `U2R`.

**Why 5-class and not binary.** A binary attack/normal detector hides the finding. The collapse
under distribution shift is concentrated in two specific families (R2L, U2R); collapsing to binary
averages that away. We report the binary view *as well* (`binary_detection` in every metrics file)
because that is what an operator's alarm actually does, but the modelling target is 5-class.

**Why not 38-class (per attack type).** 17 of the 37 types have zero training examples. A 38-class
target would make the task formally impossible for those, rather than making the *generalisation
failure* visible — which is what we want to measure.

---

## 2. Data handling

### Split protocol — the central methodological point

| Protocol | Definition | Used for |
|---|---|---|
| **A** | Concatenate `KDDTrain+` and `KDDTest+` (148,517 rows), shuffle, stratified 80/20 split | The controlled comparison *only*. Never used to report SENTINEL's performance. |
| **B** | Train on `KDDTrain+` (125,973), test on `KDDTest+` (22,544), as the dataset authors designed | **Every performance number we claim.** |

Protocol A is included because it is what a large fraction of published and student work does, not
because we endorse it. `experiment_leakage.py` holds model, features, hyperparameters and seed
constant across A and B so the difference is attributable to the split alone.

**Why A inflates the score.** Two mechanisms, both destroyed by pooling:
1. **Novel-attack destruction.** The 17 test-only attack types get scattered across both sides of a
   random split, so the model trains on examples of every type it is tested on. The zero-shot
   requirement disappears.
2. **Prior alignment.** Pooling forces train and test priors to match. Protocol B has R2L at 15.5×
   and U2R at 21.5× their training frequency; Protocol A removes that shift by construction.

We deliberately do **not** claim "duplicate row leakage" as a mechanism — NSL-KDD has 0 exact
duplicate rows in `KDDTrain+` (verified, `dataset_summary.json`). That is the fix NSL made over
KDD'99, and attributing the gap to duplicates would be wrong.

### Feature encoding

- 38 numeric features passed through unchanged.
- 3 categorical features (`protocol_type` 3 values, `service` 70, `flag` 11) one-hot encoded to
  **122 total features**.
- **The one-hot vocabulary is built from `KDDTrain+` only.** A `service` or `flag` value that
  appears only in test encodes as all-zeros for that group. This is not a bug — it is the correct
  production behaviour when a deployed detector meets a protocol it has never seen, and building
  the vocabulary from the pooled data would be a second, subtler form of test leakage.
- **`StandardScaler` is fitted inside a `Pipeline`**, so scaling statistics come from training
  folds only and never leak across CV folds.

### Field 43 (`difficulty`) is excluded

`KDDTrain+`/`KDDTest+` carry a 43rd column recording how many of the 21 original KDD'99 learners
classified that record correctly. It is a property of *the benchmark*, not of the traffic, and it
correlates strongly with label difficulty. Using it as an input is label leakage. It is dropped in
`config.py` and never reaches a model. (A surprising amount of published work on this dataset does
not drop it.)

### Attack-family mapping

The 38 labels map to 4 attack families + Normal using the canonical KDD'99 taxonomy
(`config.py::ATTACK_FAMILY`). `data.py::load_raw` raises if any label in either split is unmapped,
so a silent mis-mapping cannot pass unnoticed.

---

## 3. Metric selection

**Metric of record: macro-F1 on the official test split.** Justification: the majority-class
baseline achieves **43.1% accuracy**, and a model that ignores R2L and U2R entirely — 13.1% of the
test set, and the two families that indicate actual compromise — can still reach 86.9%.
Accuracy is reported for comparability with the literature, never as the headline.

Also reported for every model:

| Metric | Question it answers |
|---|---|
| Macro-F1 | Does the model handle rare classes at all? |
| Balanced accuracy | Mean per-class recall, insensitive to prior shift |
| **Per-class recall** | Which specific families fail? (the finding lives here) |
| Detection rate (binary) | Of all attacks, how many raised any alarm? |
| False-alarm rate | Of all normal traffic, how much was flagged? |
| Unseen-attack miss rate | Of the 3,750 novel-type flows, how many were cleared as normal? |
| p50/p99 latency, model size | Can it actually be deployed? |

**Asymmetric costs are acknowledged, not modelled.** A missed intrusion on a defence network and a
five-minute analyst distraction are not comparable, but we have no principled cost ratio, so we
report detection and false-alarm rates separately and expose τ as a policy dial rather than
inventing a cost matrix.

---

## 4. Model selection and comparison

8 configurations, all trained on identical feature matrices with `random_state=42`:

| # | Model | Why included |
|---|---|---|
| 00 | Majority-class baseline | Floor. Without it, "77% accuracy" is uninterpretable (majority = 43%). |
| 01 | Logistic regression | Linear reference; well-calibrated probabilities for the abstention channel. |
| 02 | Decision tree (depth 20) | Single-model interpretable reference. |
| 03 | Random forest (300) | The reflexive choice for this dataset; the one to beat. |
| 04 | Random forest, `balanced_subsample` | Tests whether the rare-class collapse is a loss-weighting artefact. |
| 05 | XGBoost (400, depth 8) | Strong tabular gradient boosting. |
| 06 | LightGBM (400, 63 leaves) | Second boosting implementation — guards against one library's quirks. |
| 07 | MLP (128, 64) | Non-linear, non-tree function class. |

**Two scores per model, deliberately:**
- **3-fold stratified CV macro-F1 on `KDDTrain+`** — in-distribution performance and its variance.
- **Macro-F1 on `KDDTest+`** — performance under shift.

The difference is reported as `shift_penalty_macro_f1`. Separating these is what lets us say
"the protocol dominates the model" quantitatively rather than rhetorically.

**No hyperparameter tuning was performed on the test split.** Settings are conventional defaults
chosen a priori. This is deliberate: tuning against `KDDTest+` would reintroduce exactly the
optimism the project exists to measure. A consequence is that these are not the best achievable
numbers for each family — which is fine, because the claim is about the *gap*, and tuning would
have to close a 0.40 macro-F1 gap to threaten it.

**Integer targets everywhere.** All models receive integer-encoded labels, mapped back to family
names before scoring. Required by XGBoost, and it works around a scikit-learn 1.8.0 defect where
`MLPClassifier(early_stopping=True)` crashes on string labels (`np.isnan` on a string array).
Documented in `experiment_models.py`.

---

## 5. Zero-day evaluation

Two complementary protocols, because each has a weakness the other covers.

**(a) The dataset's own shift.** `KDDTest+` contains 17 attack types absent from training. This is
realistic but uncontrolled — novelty is confounded with the prior shift.

**(b) Leave-One-Family-Out.** For each family F: delete every F row from training, refit from
scratch, then measure detection on F in the test set. Controlled — the only thing that changes is
whether F was ever seen — at the cost of being coarser (4 families, not 17 types).

Both are reported. (b) confirms (a) is not an artefact of the prior shift: Probe detection falls
0.749 → 0.369 purely from removing Probe from training, with priors otherwise unchanged.

---

## 6. The proposed fix

**Design constraint.** The failure is structural: a softmax over 5 known classes cannot express
"none of these." Any fix must add an output the classifier does not have, or a channel the
classifier does not use. We do both.

**Channel A — supervised + abstention.** Logistic regression, chosen over the marginally-better MLP
because (i) its probabilities are better behaved for thresholding than a forest's vote share or an
MLP's softmax, and (ii) it exports to a 4.9 KB ONNX model at 0.013 ms/flow. If
`max P(class) < τ` and the argmax is `Normal`, emit `SUSPICIOUS_UNCLASSIFIED` instead of clearing
the flow.

**Channel B — unsupervised novelty.** `IsolationForest(n_estimators=300, contamination=0.02)`
fitted on the **67,343 `Normal` training rows only**. It never sees an attack during training, so
it cannot be biased toward the 22 known attack types. This is the crux of why it works.

**Combination.** `alarm = A says attack OR A abstains OR B says outlier`. A union (rather than a
weighted vote) because the two channels fail in uncorrelated ways and a missed attack is the
expensive error.

**Threshold selection.** τ is swept over 11 values and the full operating curve reported. The
"recommended" point (τ=0.95) is defined by an explicit, stated rule — maximise unseen-attack
detection subject to false-alarm rate ≤ 10% — not chosen by inspection. `app/service.py` reads τ
from the metrics JSON so code and reported numbers cannot drift apart.

**Honest accounting.** Channel B alone achieves 0.566 unseen-attack detection at 0.020 false-alarm
rate, beating the supervised classifier's 0.415 at 0.070. We report this even though it somewhat
undercuts the supervised component, because it is the most informative result in the ablation.

---

## 7. Explainability

**Permutation importance** (`sklearn.inspection.permutation_importance`, 3 repeats, 6,000-row
subsample of `KDDTest+`, scored by macro-F1 drop). Computed on the **test** split on purpose: we
want the features the model relies on *under shift*, which is not necessarily what it relied on
during training.

**SHAP** (`TreeExplainer`, exact for tree ensembles) on a **stratified** sample — up to 200 flows
per family — so that U2R (200 test rows total) is represented rather than drowned out. Reported as
mean |SHAP| per class, i.e. per attack family, because "which behaviours indicate a Probe" is the
question a viva will ask.

**Feature-group roll-up.** Each feature is attributed to one of the four documented NSL-KDD blocks
(basic / content / time-based traffic / host-based traffic), so importance can be discussed as
network semantics rather than column indices.

Both are computed on the Random Forest rather than the best model, because `TreeExplainer` is exact
and fast on it and its macro-F1 (0.494) is within 0.052 of the best (0.546) — close enough that the
qualitative attribution transfers. Stated rather than glossed.

---

## 8. Reproducibility engineering

- **Single seed constant** (`config.SEED = 42`) used by every split, model and sampler.
- **Idempotent stages.** Every script detects its own completed output and skips. `data.py` skips
  files already downloaded; `experiment_models.py` writes a per-model JSON checkpoint after each
  model and skips models already done; `experiment_zeroday.py` checkpoints after each LOFO family.
  A crash in stage N never destroys stages 1..N−1 — a property added after a container reset
  destroyed an uncheckpointed run during development.
- **SHA-256 manifest** for every raw file (`data/raw/manifest.json`) so byte-level equality of the
  input data is verifiable.
- **Pinned dependencies** in `requirements.txt`, generated from the actually-installed versions
  rather than written by hand.
- **Every number in the README is read from a JSON file in `reports/metrics/`.** None were typed
  manually, so the documentation cannot silently disagree with the code.
- **Raw data is not committed** (28 MB); `python src/data.py` reconstructs it.

---

## 9. Threats to validity

| Threat | Assessment |
|---|---|
| Dataset age (1999 traffic) | Real and unfixable here. The *methodological* claim is about evaluation protocol and transfers to any dataset with a designed shift; absolute numbers do not transfer to 2026 networks. |
| Single dataset | The strongest available criticism. Cross-dataset validation (train NSL-KDD → test UNSW-NB15) was planned; those hosts are 403-blocked from the build environment. Stated as future work, not quietly omitted. |
| Untuned hyperparameters | Would raise all test scores somewhat. Cannot plausibly close a 0.40 macro-F1 gap, and tuning on the test split would be the very error under study. |
| Only one seed | Point estimates on the fixed official split; CV standard deviations are reported for the in-distribution scores. Multi-seed repeats are future work. |
| Attribution model ≠ best model | Explainability computed on Random Forest, not the MLP. Justified by exactness of `TreeExplainer` and a 0.05 macro-F1 gap; stated openly. |
| Latency measured on 2 vCPU container | Absolute numbers are hardware-dependent. The **ratios** (ONNX logreg 5,000× faster than Random Forest) are the transferable result. |
