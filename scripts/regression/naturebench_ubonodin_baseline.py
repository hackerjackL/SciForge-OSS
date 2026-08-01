#!/usr/bin/env python3
"""SciForge-OSS NatureBench reproducible baseline — ubonodin_rnap_inhibition regression.

Reproduces the v1.3.0 baseline run (Pearson 0.473 / Spearman 0.385 / MAE 2.24)
from the source task files. Zero paid API; sklearn + pandas + scipy only.

Usage:
    python3 scripts/regression/naturebench_ubonodin_baseline.py \
        [--train datasets/NatureBench/ubonodin_run/train.csv] \
        [--test .../test_input.csv] [--gt .../ground_truth.csv]

Outputs predictions.csv + score.json into the run dir (default: same dir as --train).
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler

AAS = "ACDEFGHIKLMNPQRSTVWY"


def featurize(full_seq: str) -> np.ndarray:
    """21-dim feature: 20 AA composition + mean position index."""
    s = str(full_seq)
    f = [s.count(a) / max(len(s), 1) for a in AAS]
    f.append(np.mean([AAS.index(c) + 1 for c in s]) / 20.0)
    return np.array(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default="datasets/NatureBench/ubonodin_run/train.csv")
    ap.add_argument("--test", default="datasets/NatureBench/ubonodin_run/test_input.csv")
    ap.add_argument("--gt", default="datasets/NatureBench/ubonodin_run/ground_truth.csv")
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--out", default=None, help="output dir (default: train dir)")
    args = ap.parse_args()

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    Xtr = np.array([featurize(s) for s in train["Full_Sequence"]])
    ytr = train["Score"].values
    Xte = np.array([featurize(s) for s in test["Full_Sequence"]])
    assert not np.isnan(Xtr).any(), "NaN in features — check Full_Sequence column"

    sc = StandardScaler().fit(Xtr)
    model = Ridge(alpha=args.alpha).fit(sc.transform(Xtr), ytr)
    pred = model.predict(sc.transform(Xte))

    out_dir = args.out or os.path.dirname(os.path.abspath(args.train))
    os.makedirs(out_dir, exist_ok=True)
    pd.DataFrame({"Score": pred}).to_csv(os.path.join(out_dir, "predictions.csv"), index=False)

    gt = pd.read_csv(args.gt)
    metrics = {
        "ubonodin_rnap_inhibition": {
            "Pearson Correlation": round(float(pearsonr(gt["Score"].values, pred)[0]), 6),
            "Spearman Correlation": round(float(spearmanr(gt["Score"].values, pred)[0]), 6),
            "MAE": round(float(mean_absolute_error(gt["Score"].values, pred)), 6),
        }
    }
    with open(os.path.join(out_dir, "score.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
