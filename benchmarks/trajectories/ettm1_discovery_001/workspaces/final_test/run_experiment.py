import json
from benchmarks.runners.baseline_runner import run_baseline
config = json.load(open('experiment_config.json'))
summary = run_baseline('ettm1', 'dlinear', data_root='C:\\Users\\Admin（无密码）\\Documents\\Codex\\2026-09-22\\github-https-github-com-benjamindaoson-ai\\work\\ai-scientist\\data\\ettm1', max_windows=1024, evaluation_split='test', persist=False, model_kwargs=config)
json.dump(summary, open('metrics.json', 'w'), indent=2)
