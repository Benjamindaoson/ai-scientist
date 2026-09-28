# Retrieval Benchmark Report

## Frozen benchmark

- Questions: 100
- Recall@10: 1.0
- Recall@20: 1.0
- Recall@50: 1.0
- MRR: 0.8476666666666668
- Dangerous-prior recall: 1.0
- External-prior recall: 1.0
- False-positive rate: 0.015
- Inspectable source rate: 1.0
- Fabricated IDs: 0

Each production question records its designated dangerous/closest prior, two false-friend IDs, and a source chunk. The JSON fixture is frozen at `benchmarks/literature/known_prior_production_v1.json`.
