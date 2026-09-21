"""Run public TableShift diabetes_readmission with a locked ID/OOD evaluator."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

def _candidate_classifier(seed):
    path=Path("candidate.py")
    if not path.exists(): return None
    text=path.read_text(encoding="utf-8",errors="ignore").lower()
    forbidden=("ood_test","get_dataset(","tableshift")
    if any(x in text for x in forbidden):
        raise RuntimeError("PROTOCOL_VIOLATION: candidate.py attempts to access benchmark split/data API")
    spec=importlib.util.spec_from_file_location("benchmark_candidate",path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.build_classifier(seed) if hasattr(mod,"build_classifier") else None

def main():
    p=argparse.ArgumentParser(); p.add_argument("--cache-dir",required=True); p.add_argument("--seed",type=int,default=2021); args=p.parse_args()
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder,StandardScaler
    from tableshift import get_dataset

    dset=get_dataset("diabetes_readmission",cache_dir=args.cache_dir)
    Xtr,ytr,_,_=dset.get_pandas("train"); Xid,yid,_,_=dset.get_pandas("id_test"); Xood,yood,_,_=dset.get_pandas("ood_test")
    numeric=list(Xtr.select_dtypes(include=["number","bool"]).columns); categorical=[c for c in Xtr.columns if c not in numeric]
    use_scale=os.getenv("AI_SCIENTIST_COMPONENT_STANDARDIZATION","1")!="0"
    use_l2=os.getenv("AI_SCIENTIST_COMPONENT_L2_REGULARIZATION","1")!="0"
    num_steps=[("imp",SimpleImputer(strategy="median"))]
    if use_scale: num_steps.append(("scale",StandardScaler()))
    pre=ColumnTransformer([
        ("num",Pipeline(num_steps),numeric),
        ("cat",Pipeline([("imp",SimpleImputer(strategy="most_frequent")),("onehot",OneHotEncoder(handle_unknown="ignore"))]),categorical),
    ])
    clf=_candidate_classifier(args.seed) or LogisticRegression(max_iter=500,random_state=args.seed,C=1.0 if use_l2 else 1e6)
    model=Pipeline([("pre",pre),("clf",clf)]); model.fit(Xtr,ytr)
    id_acc=accuracy_score(yid,model.predict(Xid)); ood_acc=accuracy_score(yood,model.predict(Xood))
    metrics={"id_accuracy":float(id_acc),"ood_accuracy":float(ood_acc),"ood_gap":float(id_acc-ood_acc)}
    Path("metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")

if __name__=="__main__": main()
