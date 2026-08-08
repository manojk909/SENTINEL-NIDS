# Dataset — NSL-KDD

## Provenance

- **Dataset:** NSL-KDD, the de-duplicated and re-balanced revision of the KDD Cup 1999 network
  intrusion dataset.
- **Original authors:** M. Tavallaee, E. Bagheri, W. Lu, A. A. Ghorbani, *"A Detailed Analysis of
  the KDD CUP 99 Data Set"*, IEEE CISDA 2009. Produced at the Canadian Institute for
  Cybersecurity, University of New Brunswick.
- **Retrieved from:** public GitHub mirror `https://raw.githubusercontent.com/HoaNP/NSL-KDD-DataSet/master/`
  on 08 Aug 2026. The canonical UNB host (`unb.ca/cic/datasets/nsl.html`) and UCI were unreachable
  from the build environment; the mirror's `KDDTrain+`/`KDDTest+` row counts (125,973 / 22,544) and
  label vocabulary match the published specification exactly, which validates the copy.
- **Licence:** NSL-KDD is distributed for research and educational use. Used here for a
  non-commercial academic hackathon submission with attribution.
- **Reproduce:** `python src/data.py` — idempotent, skips files already present, writes
  `data/raw/manifest.json` with SHA-256 for every file.

## Files

| File | Rows | Purpose |
|---|---|---|
| `KDDTrain+.txt` | 125,973 | Official training split |
| `KDDTest+.txt` | 22,544 | **Official test split — contains unseen attack types** |
| `KDDTrain+_20Percent.txt` | 25,192 | Official 20% subsample of train |
| `KDDTest-21.txt` | 11,850 | Test subset excluding records all 21 KDD'99 learners classified correctly (the *hard* subset) |

## Schema

43 comma-separated fields, no header row:

- **Fields 1–41** — features. 38 numeric, 3 categorical (`protocol_type` (3 values),
  `service` (70 values), `flag` (11 values)).
- **Field 42** — `label`: `normal` or one of 37 attack type names.
- **Field 43** — `difficulty`: number of the 21 original KDD'99 learners that classified the record
  correctly. **Not a feature.** It is a property of the benchmark, not of the traffic, and using it
  as an input is a form of label leakage. It is excluded from all models here.

Feature names are defined in `src/config.py::COLUMNS`.

### Feature groups
- *Basic* (1–9): duration, protocol, service, flag, byte counts, flags.
- *Content* (10–22): payload-derived — failed logins, root shell, file creations. These carry the
  signal for R2L/U2R attacks.
- *Time-based traffic* (23–31): statistics over a 2-second window. Signal for DoS/Probe.
- *Host-based traffic* (32–41): statistics over a 100-connection window. Signal for slow scans.

## Label taxonomy

The 38 labels map to 5 classes (mapping in `src/config.py::ATTACK_FAMILY`):

| Class | Meaning | Train | Test | Prior shift |
|---|---|---|---|---|
| Normal | Benign traffic | 67,343 (53.5%) | 9,711 (43.1%) | 0.8× |
| DoS | Denial of service | 45,927 (36.5%) | 7,458 (33.1%) | 0.9× |
| Probe | Scanning / surveillance | 11,656 (9.3%) | 2,421 (10.7%) | 1.2× |
| **R2L** | Remote-to-local intrusion | **995 (0.79%)** | **2,754 (12.2%)** | **15.5×** |
| **U2R** | Privilege escalation | **52 (0.04%)** | **200 (0.89%)** | **21.5×** |

## The two properties that make this dataset the right choice

**1. Built-in unseen-attack benchmark.** 17 of the 37 attack types occur *only* in `KDDTest+`:

```
apache2, httptunnel, mailbomb, mscan, named, processtable, ps, saint, sendmail,
snmpgetattack, snmpguess, sqlattack, udpstorm, worm, xlock, xsnoop, xterm
```

These account for **3,750 test records (16.6% of the test set)**. A model is therefore required to
generalise to attacks it has never observed — which is the actual operational condition.

**2. Severe, *shifting* class imbalance.** R2L and U2R are ~0.8% of training data combined but
~13.1% of the test set. Any model tuned to maximise accuracy on the training distribution will
under-weight exactly the two categories that represent successful compromise rather than mere
disruption.

Together these mean: **pooling train+test and re-splitting at random destroys both properties.**
That is the error this project measures. See `docs/PROBLEM_STATEMENT.md`.

## Known limitations (stated up front)

- Traffic is from a 1998/1999 DARPA simulation. Protocol mix, encryption rates and attack tooling
  have all changed substantially; absolute numbers here should not be read as 2026 operational
  performance.
- Attacks are synthetic and injected, so base rates do not reflect any real network.
- Features are hand-engineered flow aggregates, not raw packets, so the model inherits whatever the
  1999 feature designers considered relevant.

These are limitations of the *benchmark*, not of the methodological finding — the leakage effect
demonstrated here is a property of the evaluation protocol and reproduces on any dataset with a
designed train/test shift.

## Not committed to git

The raw `.txt` files (~28 MB) are excluded via `.gitignore`. Run `python src/data.py` to fetch
them; SHA-256 hashes in `data/raw/manifest.json` let you verify you have identical bytes.
