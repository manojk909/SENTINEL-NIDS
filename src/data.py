"""Data acquisition and preprocessing for SENTINEL-NIDS.

Idempotent: re-running will not re-download files that already exist and validate.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request

import numpy as np
import pandas as pd

from config import (ATTACK_FAMILY, CATEGORICAL, COLUMNS, DATA_PROC, DATA_RAW,
                    FILES, MIRROR, NOVEL_ATTACKS, SEED)


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(force: bool = False) -> dict:
    """Fetch NSL-KDD files into data/raw. Skips files already present (checkpoint-safe)."""
    manifest = {}
    for name in FILES:
        dest = DATA_RAW / name
        if dest.exists() and dest.stat().st_size > 0 and not force:
            print(f"[data] cached  {name} ({dest.stat().st_size:,} bytes)")
        else:
            url = MIRROR + name.replace("+", "%2B") if False else MIRROR + name
            print(f"[data] fetching {name}")
            urllib.request.urlretrieve(url, dest)
        manifest[name] = {"bytes": dest.stat().st_size, "sha256": sha256(dest)}
    (DATA_RAW / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load_raw(split: str) -> pd.DataFrame:
    """split in {'train','test','train20','test21'}"""
    fname = {"train": "KDDTrain+.txt", "test": "KDDTest+.txt",
             "train20": "KDDTrain+_20Percent.txt", "test21": "KDDTest-21.txt"}[split]
    df = pd.read_csv(DATA_RAW / fname, names=COLUMNS)
    unmapped = set(df["label"].unique()) - set(ATTACK_FAMILY)
    if unmapped:
        raise ValueError(f"Unmapped attack labels in {split}: {sorted(unmapped)}")
    df["family"] = df["label"].map(ATTACK_FAMILY)
    df["is_attack"] = (df["family"] != "Normal").astype(int)
    df["is_novel"] = df["label"].isin(NOVEL_ATTACKS).astype(int)
    return df


def build_feature_matrix(train: pd.DataFrame, *others: pd.DataFrame):
    """One-hot encode categoricals with the TRAIN vocabulary only (no test leakage).

    Unseen categorical values in test are encoded as all-zeros for that feature group,
    which is the honest behaviour for a deployed system meeting a novel service/flag.
    """
    frames = [train, *others]
    encoded = []
    numeric = [c for c in COLUMNS if c not in CATEGORICAL + ["label", "difficulty"]]

    vocab = {c: sorted(train[c].unique()) for c in CATEGORICAL}
    for df in frames:
        parts = [df[numeric].reset_index(drop=True).astype(float)]
        for c in CATEGORICAL:
            d = pd.DataFrame(
                {f"{c}__{v}": (df[c] == v).astype(float).values for v in vocab[c]}
            )
            parts.append(d)
        encoded.append(pd.concat(parts, axis=1))

    cols = encoded[0].columns
    encoded = [e.reindex(columns=cols, fill_value=0.0) for e in encoded]
    return encoded, list(cols), vocab


def summarise() -> dict:
    """Dataset facts used in the report/deck. Written to reports/metrics/dataset_summary.json."""
    tr, te = load_raw("train"), load_raw("test")
    tr_types, te_types = set(tr.label.unique()), set(te.label.unique())
    s = {
        "train_rows": int(len(tr)),
        "test_rows": int(len(te)),
        "n_features_raw": 41,
        "exact_duplicate_rows_train": int(tr.duplicated().sum()),
        "attack_types_train": len(tr_types),
        "attack_types_test": len(te_types),
        "attack_types_test_only": sorted(te_types - tr_types),
        "n_attack_types_test_only": len(te_types - tr_types),
        "novel_rows_in_test": int(te.is_novel.sum()),
        "novel_share_of_test": round(float(te.is_novel.mean()), 4),
        "family_counts_train": tr.family.value_counts().to_dict(),
        "family_counts_test": te.family.value_counts().to_dict(),
        "attack_rate_train": round(float(tr.is_attack.mean()), 4),
        "attack_rate_test": round(float(te.is_attack.mean()), 4),
    }
    (DATA_PROC / "dataset_summary.json").write_text(json.dumps(s, indent=2, default=str))
    return s


if __name__ == "__main__":
    download()
    s = summarise()
    print(json.dumps(s, indent=2, default=str)[:2000])
