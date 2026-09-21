"""Run the official PatchTST supervised benchmark and emit normalized metrics.json."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HORIZONS=(96,192,336,720)
DATASETS={
    "ETTm1":{"data":"ETTm1","path":"ETTm1.csv","enc_in":7,"freq":"t"},
    "weather":{"data":"custom","path":"weather.csv","enc_in":21,"freq":"h"},
}

def parse_last_result(result_file: Path) -> tuple[float,float]:
    text=result_file.read_text(encoding="utf-8",errors="ignore")
    matches=re.findall(r"mse:([0-9.eE+-]+),\s*mae:([0-9.eE+-]+)",text)
    if not matches: raise RuntimeError("PatchTST result.txt did not contain mse/mae")
    mse,mae=matches[-1]; return float(mse),float(mae)

def run_one(root: Path,dataset: str,pred_len: int,seed: int,epochs: int,model: str,revin: bool) -> tuple[float,float,int]:
    cfg=DATASETS[dataset]; supervised=root/"PatchTST_supervised"; result_file=supervised/"result.txt"
    before=result_file.read_text(encoding="utf-8",errors="ignore") if result_file.exists() else ""
    checkpoints_before={p: p.stat().st_mtime_ns for p in supervised.glob("checkpoints/**/checkpoint.pth")}
    cmd=[
        sys.executable,"run_longExp.py","--random_seed",str(seed),"--is_training","1",
        "--root_path","./dataset/","--data_path",cfg["path"],
        "--model_id",f"bench_{dataset}_336_{pred_len}","--model",model,"--data",cfg["data"],"--features","M",
        "--seq_len","336","--pred_len",str(pred_len),
        "--enc_in",str(cfg["enc_in"]),"--dec_in",str(cfg["enc_in"]),"--c_out",str(cfg["enc_in"]),
        "--e_layers","3","--n_heads","16","--d_model","128","--d_ff","256",
        "--dropout","0.2","--fc_dropout","0.2","--head_dropout","0",
        "--patch_len","16","--stride","8","--revin","1" if revin else "0","--des","BenchV1",
        "--train_epochs",str(epochs),"--patience","10","--lradj","type3",
        "--itr","1","--batch_size","128","--learning_rate","0.0001","--freq",cfg["freq"],
    ]
    proc=subprocess.run(cmd,cwd=supervised,text=True,capture_output=True,check=False)
    if proc.returncode!=0: raise RuntimeError(f"PatchTST failed for {dataset}/{pred_len}: {proc.stderr[-4000:]}")
    if not result_file.exists(): raise RuntimeError("PatchTST did not create result.txt")
    after=result_file.read_text(encoding="utf-8",errors="ignore")
    if after==before: raise RuntimeError("PatchTST result.txt was not updated")
    candidates=[]
    for p in supervised.glob("checkpoints/**/checkpoint.pth"):
        old=checkpoints_before.get(p)
        if old is None or p.stat().st_mtime_ns>old: candidates.append(p)
    checkpoint_bytes=max((p.stat().st_size for p in candidates),default=0)
    mse,mae=parse_last_result(result_file); return mse,mae,checkpoint_bytes

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True); p.add_argument("--seed",type=int,default=2021)
    p.add_argument("--epochs",type=int,default=30); p.add_argument("--model",default="PatchTST")
    args=p.parse_args(); root=Path(args.upstream).resolve()
    if not (root/"PatchTST_supervised"/"run_longExp.py").exists(): raise SystemExit("Expected official PatchTST checkout at --upstream")
    patching=os.getenv("AI_SCIENTIST_COMPONENT_PATCHING","1")!="0"
    revin=os.getenv("AI_SCIENTIST_COMPONENT_REVIN","1")!="0"
    model=args.model
    if args.model=="PatchTST" and not patching: model="DLinear"
    rows=[]
    for dataset in DATASETS:
        for horizon in HORIZONS:
            mse,mae,bytes_=run_one(root,dataset,horizon,args.seed,args.epochs,model,revin)
            rows.append({"dataset":dataset,"horizon":horizon,"mse":mse,"mae":mae,"checkpoint_bytes":bytes_})
    metrics={
        "mse":sum(r["mse"] for r in rows)/len(rows),
        "mae":sum(r["mae"] for r in rows)/len(rows),
        "checkpoint_bytes":max((r["checkpoint_bytes"] for r in rows),default=0),
        "conditions":len(rows),"details":rows,
    }
    (root/"metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")

if __name__=="__main__": main()
