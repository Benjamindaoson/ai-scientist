"""Run public TableShift diabetes_readmission with a deterministic sklearn baseline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(); p.add_argument("--cache-dir", required=True); p.add_argument("--seed", type=int, default=2021)
    args=p.parse_args()
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from tableshift import get_dataset

    dset=get_dataset("diabetes_readmission", cache_dir=args.cache_dir)
    Xtr,ytr,_,_=dset.get_pandas("train")
    Xid,yid,_,_=dset.get_pandas("id_test")
    Xood,yood,_,_=dset.get_pandas("ood_test")
    numeric=list(Xtr.select_dtypes(include=["number","bool"]).columns)
    categorical=[c for c in Xtr.columns if c not in numeric]
    pre=ColumnTransformer([
        ("num", Pipeline([("imp",SimpleImputer(strategy="median")),("scale",StandardScaler())]), numeric),
        ("cat", Pipeline([("imp",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    model=Pipeline([("pre",pre),("clf",LogisticRegression(max_iter=500, random_state=args.seed))])
    model.fit(Xtr,ytr)
    id_acc=accuracy_score(yid,model.predict(Xid)); ood_acc=accuracy_score(yood,model.predict(Xood))
    metrics={"id_accuracy":float(id_acc),"ood_accuracy":float(ood_acc),"ood_gap":float(id_acc-ood_acc)}
    Path("metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")


if __name__=="__main__": main()
