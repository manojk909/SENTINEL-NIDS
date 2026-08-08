# Round 2 Prep — Online Model Explanation Round (16 Aug 2026, 10:00–17:00 IST)

The round is explicitly about *explaining* the model: "participants must present and explain their
proposed Machine Learning solution, demonstrating their understanding of the problem, dataset,
methodology, and expected outcomes."

So the currency is **understanding, not results**. Below: the numbers to have memorised, the
questions most likely to come, and honest answers to the hostile ones.

---

## Numbers to know cold

| Quantity | Value |
|---|---|
| Train / test rows | 125,973 / 22,544 |
| Features | 41 raw → 122 after one-hot |
| Attack types train / test | 22 / 37 |
| **Attack types test-only** | **17** (3,750 rows = 16.6% of test) |
| Protocol A (pooled random split) | acc **0.9951**, macro-F1 **0.9548** |
| Protocol B (official split) | acc **0.7528**, macro-F1 **0.4869** |
| Gap | 24.23 acc points, 46.79 macro-F1 points, **50.4× error rate** |
| R2L recall A → B | 0.915 → **0.038** |
| U2R recall A → B | 0.780 → **0.005** |
| Unseen attacks cleared as "normal" | **76.7%** |
| Class prior shift | R2L **15.5×**, U2R **21.5×** |
| Best model (macro-F1, honest) | MLP (128,64) **0.5460** |
| Majority baseline accuracy | 0.4308 |
| Channel B alone, unseen detection | **0.566** at FAR **0.020** |
| Hybrid at τ=0.95 | unseen **0.659**, FAR **0.093** |
| Improvement | **+24.4 pp coverage for +2.2 pp false alarms** |
| ONNX latency / size | **0.013 ms** p50, **4.9 KB**, 809,931 flows/s |
| Random forest latency / size | 65.2 ms, 38.4 MB (**5,055× slower**) |
| Feature-group importance | Basic 51.7%, Host-based 35.4%, Time-based 11.7%, **Content 1.2%** |

---

## The 90-second opening

> Machine-learning intrusion detection reports 97–99% accuracy in the literature. I tested whether
> that number survives contact with reality. I took one model, one feature pipeline, one seed, and
> changed only one thing: the train/test split. Accuracy went from 99.51% to 75.28%, and macro-F1
> from 0.955 to 0.487 — a 50× higher error rate. The reason is that NSL-KDD's official test set
> contains 17 attack types that never appear in training, and pooling the splits destroys that.
> Under honest evaluation the detector silently labels 76.7% of never-before-seen attacks as normal
> traffic. So I built a fix: a second channel trained only on normal traffic, plus explicit
> abstention. That raises unseen-attack coverage from 41.5% to 65.9% for 2.2 points of extra false
> alarms, and it runs in 0.013 milliseconds per flow in a 4.9 KB model. It still misses 34% of
> unseen attacks — I'll show you exactly where and why.

---

## Likely questions — and answers

### On the core claim

**Q: Isn't this just data leakage? Everyone knows not to leak.**
Not classical leakage — there are **zero duplicate rows** in `KDDTrain+`; that was NSL's fix over
KDD'99. The mechanism is different and more interesting: pooling destroys two *designed* properties —
the 17 test-only attack types, and a 15–21× class-prior shift. It is a distribution-shift error, not
a duplicate-row error. I checked the duplicate hypothesis specifically and ruled it out.

**Q: Why should I care? The dataset is from 1999.**
The dataset's age limits the *absolute numbers*, not the *finding*. The finding is about evaluation
protocol, and it reproduces on any dataset with a designed train/test shift. I state the age
limitation in the model card rather than hiding it. I'd also note the alternative was worse:
UNSW-NB15 and CIC-IDS2017 were unreachable from my build environment, and NSL-KDD is the only common
benchmark that ships a documented unseen-attack test protocol — which is precisely what makes the
controlled experiment possible.

**Q: Your best macro-F1 is 0.55. Isn't that a bad model?**
Yes — and that is the honest number. A team reporting 0.99 on this dataset has almost certainly
random-split it. I can produce 0.955 in one line of code; I've included it as Protocol A to show it
is meaningless. I'd rather present a defensible 0.55 than an indefensible 0.99.

**Q: Did you just pick the split that made your point?**
The opposite — Protocol B is the split the dataset authors designed and shipped. Protocol A is the
deviation. I use the authors' protocol for every number I claim.

### On methodology

**Q: You didn't tune hyperparameters. Wouldn't tuning change the conclusion?**
Tuning would raise all test scores somewhat, but the gap is ~0.40 macro-F1 — tuning does not close
that. More importantly, tuning *against the test split* would commit the exact error I'm measuring.
Untuned defaults across all 8 models keep the comparison clean.

**Q: Why macro-F1 and not accuracy?**
The majority baseline gets 43.1% accuracy. A model that ignores R2L and U2R entirely — 13.1% of the
test set, and the only two families that mean an attacker actually got in — still scores well on
accuracy. Accuracy cannot see the failure. Macro-F1 and per-class recall can.

**Q: Why 5 classes rather than binary?**
Binary averages away the finding. The collapse is concentrated in R2L and U2R specifically. I report
the binary view too, because that's what an operator's alarm does, but modelling 5 classes is what
makes the failure visible.

**Q: You dropped the 43rd column. Why?**
`difficulty` records how many of the 21 original KDD'99 learners got that record right. It's a
property of the benchmark, not the traffic, and it correlates with label difficulty — using it is
label leakage. A surprising amount of published work leaves it in.

**Q: Only 3 CV folds and one seed?**
A time constraint I'll name honestly. 3-fold on 126k rows is stable (SDs are in the JSON), and the
test-split numbers are point estimates on a fixed official split, so CV variance isn't the binding
uncertainty. Multi-seed repeats are the first thing I'd add.

### On the fix

**Q: Your unsupervised channel beats your supervised one on unseen attacks. Doesn't that make the supervised model pointless?**
It's my favourite result, and no. Channel B wins on *unseen* attacks (0.566 vs 0.415) at a third the
false-alarm rate, but loses on *seen* attacks (0.638 vs 0.756). They fail in uncorrelated ways,
which is exactly why the union beats both. What it does prove is that the supervised model's
blindness isn't a capacity problem — supervision on 22 known attack types actively misleads it about
the 17 it hasn't seen.

**Q: Isn't abstention just moving the problem to a human?**
Yes, deliberately. The alternative isn't a correct automatic answer — the model provably cannot
produce one for an attack class it has never seen. The alternative is a *silent miss*. Converting an
unknowable case into a triaged alert is the correct engineering decision, and I report the exact
cost in false alarms so the trade is explicit.

**Q: Why IsolationForest rather than an autoencoder or one-class SVM?**
IsolationForest trains in seconds on 67k rows, has one meaningful hyperparameter, and needs no
architecture search — so I can explain every part of it, which matters for this round. A one-class
SVM is O(n²)-ish and impractical at this size. An autoencoder would be a reasonable extension and I
haven't shown it's worse; I'd want to test it before claiming either way.

**Q: How did you pick τ = 0.95?**
By a stated rule, not by eye: maximise unseen-attack detection subject to false-alarm rate ≤ 10%.
The full 11-point curve is in the metrics JSON, and the service reads τ from that file so code and
paper can't drift.

### On deployment

**Q: Random Forest is standard for this. Why not use it?**
Three reasons, all measured: lower macro-F1 (0.494 vs 0.546 for the MLP, 0.540 for logistic
regression), **65 ms per flow versus 0.013 ms** for ONNX logistic regression — 5,055× slower — and
38.4 MB versus 4.9 KB. At 65 ms one worker sustains ~15 flows/second. It isn't deployable at line
rate. The linear model wins on accuracy *and* speed *and* size simultaneously.

**Q: Can this run in real time?**
Model inference, yes with large margin — 810k flows/s single-threaded covers a 1 Gbps link about 6.6×
over. But I want to be precise: that measures inference on pre-computed flow features. Building the
feature extractor from a live packet stream — connection tracking, sliding windows, per-host state —
is the harder problem and is out of scope. In a real system that, not inference, is the bottleneck.

**Q: What about adversarial attacks?**
Not addressed, and that's a genuine gap. A linear model is especially easy to evade with white-box
knowledge. Nothing in my results speaks to an adaptive adversary. It's listed as the top item in the
failure-mode table.

### On explainability (the heart of this round)

**Q: Explain one prediction.**
Take a `neptune` (SYN flood) flow. SHAP says the decision is driven by `src_bytes` near zero,
`flag=S0` (connection attempted, never established), high `same_srv_rate` and high
`dst_host_serror_rate`. In plain terms: many half-open connections to the same service on the same
host, transferring no data. That is the definition of a SYN flood, and the model is keying on exactly
the right behaviour — which is why DoS recall holds up at 0.797 even under shift.

**Q: So why does R2L fail so badly?**
This is the best question and I have a mechanistic answer. R2L and U2R are the only families driven
by **content** features — `root_shell`, `hot`, `num_file_creations`, `is_guest_login`. But
permutation importance shows content features carry only **1.2%** of total model importance, against
51.7% for basic header/byte features. The model has learned to be a traffic-pattern detector, because
98.8% of its training signal is traffic patterns. R2L and U2R look like ordinary sessions at the flow
level — a successful password guess is one normal-looking login. The features that would distinguish
them exist but are almost unused, because those two families are 0.83% of training data. That is the
causal chain, and it tells you exactly where to invest: content features and R2L/U2R sampling.

**Q: Why permutation importance on the test set, not the training set?**
Because I want the features the model relies on *under shift* — the deployed condition — not the
features it happened to fit during training. Those aren't the same thing, which is itself part of the
story.

**Q: Why did you explain the Random Forest and not your best model?**
`TreeExplainer` is exact and fast on forests, and RF's macro-F1 (0.494) is within 0.05 of the MLP
(0.546), so the qualitative attribution transfers. It's a stated approximation, in
`METHODOLOGY.md` §7 — not something I'd let pass silently.

### Hostile / meta

**Q: What did you get wrong?**
Two things. First, I initially expected class rebalancing to help — it made things measurably worse
(macro-F1 0.494 → 0.468, R2L recall 0.048 → 0.005), because reweighting a loss cannot manufacture
information about attack types absent from training. I kept it in the comparison rather than deleting
the negative result. Second, I lost an uncheckpointed experiment run to an environment failure
mid-build, which is why every stage in the repo is now independently checkpointed and idempotent.

**Q: What would you do with another month?**
In priority order: (1) cross-dataset validation — train on NSL-KDD, test on UNSW-NB15 — which is the
strongest remaining criticism; (2) attack the R2L/U2R blind spot via content features and targeted
resampling; (3) adversarial robustness evaluation; (4) multi-seed repeats with confidence intervals.

**Q: What's the single most important thing you learned?**
That the evaluation protocol mattered roughly five times more than the model choice. The spread
between my best and worst real model was 0.09 macro-F1. The spread between the two protocols was
0.47. I spent most of my time on the thing that mattered least in almost every other project I've
read — and that's the transferable lesson.

---

## Demo plan (if screen-sharing is possible)

1. `python run_all.py --only leakage` — the headline experiment, live, ~35 s.
2. `python app/service.py` — CLI smoke test replaying six real flows, chosen to show both
   successes and failures:

   | Flow | Type | Result |
   |---|---|---|
   | `normal` | benign | `NORMAL`, conf 0.984 ✓ |
   | `neptune` | known DoS | `ATTACK:DoS`, conf 0.999 ✓ |
   | `saint` | **unseen** Probe | `ATTACK:Probe`, conf 0.971 ✓ |
   | `apache2` | **unseen** DoS | `ATTACK:DoS`, conf 0.722 ✓ |
   | `snmpguess` | **unseen** R2L | `NORMAL` — **missed** ✗ |
   | `worm` | **unseen** R2L | `NORMAL` — **missed** ✗ |

   **Show the two failures, do not skip them.** The point being made is that the system
   generalises to unseen DoS and Probe attacks it was never trained on, and does *not*
   generalise to unseen R2L — exactly as the per-family numbers predict. A demo that only
   showed successes would contradict my own model card. If asked "why did you include failing
   cases in your demo" — because the alternative is a demo that lies.

3. `reports/figures/fig1` → `fig4` → `fig8` in order: the gap, where it hits, the consequence, the fix.
4. If pushed on the R2L miss, go straight to fig11 (SHAP) and the 1.2%-content-importance
   explanation — the failure has a mechanistic cause I can name.

## Things to avoid saying

- Any unqualified "99%" — always name the protocol.
- "Real-time" without the feature-extraction caveat.
- "State of the art." This is not, and does not claim to be.
- Over-claiming Channel B. It beats Channel A on unseen attacks only, and loses on seen ones.
