import json
from benchmarks.runners.baseline_runner import run_baseline
summary = run_baseline(benchmark_name='ettm1', model_name='dlinear', data_root='C:\\Users\\Admin（无密码）\\Documents\\Codex\\2026-09-22\\github-https-github-com-benjamindaoson-ai\\work\\ai-scientist\\data\\ettm1', persist=False, **{})
json.dump(summary['metrics'], open('metrics.json', 'w'), indent=2)
