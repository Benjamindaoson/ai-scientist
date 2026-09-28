# Retrieval Benchmark v2 Report

## Status

`PROVISIONAL` — eight independent reviewer-style questions cover robotics, VLA, uncertainty, intervention, world models, multimodal learning, and agent systems. The set is not a human-adjudicated 100-query benchmark and is therefore ineligible as TOPIC_READY hard evidence.

## Anti-leakage rule

Construction rejects a question when at least 65% of its tokens are copied from the designated title/abstract or when it covers at least 80% of the title tokens. Every item declares dangerous priors, closest priors, and false-friend identifiers.

## Actual BGE-M3 run

- Questions: 8
- Recall@5: 0.25
- Recall@10: 0.50
- Recall@20: 0.50
- Recall@50: 0.625
- MRR: 0.14453125
- Dangerous-prior recall: 0.625
- False-positive rate: 0.0
- Fabricated IDs: 0
- Eligible as TOPIC_READY evidence: false

The lower scores replace the invalid legacy self-retrieval claim of Recall@10 = 1.0.

