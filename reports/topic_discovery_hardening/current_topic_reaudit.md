# Current Topic Re-audit

## Previous topic

`Measurement audit for Embodied AI`

## Current status

- Novelty: `NOVELTY_UNCERTAIN`
- Feasibility: `FEASIBILITY_UNCERTAIN`
- Previous TOPIC_READY: invalidated

## Dangerous-prior regression set

The production database now contains the following source-backed records for mandatory re-audit:

1. Failure Prediction at Runtime for Generative Robot Policies (FIPER), arXiv:2510.09459
2. Perturbation-Based Epistemic Uncertainty for Failure Detection in Vision-Language-Action Models, arXiv:2606.20754
3. SAFE: Multitask Failure Detection for Vision-Language-Action Models, arXiv:2506.09937
4. Uncertainty Quantification for Flow-Based Vision-Language-Action Models, arXiv:2606.18043
5. Ask Before You Act: Token-Level Uncertainty for Intervention in Vision-Language-Action Models, OpenReview:NX0euXAv98

These papers directly pressure the previous uncertainty/failure/intervention framing. They are retrieval regressions, not hard-coded kill decisions. Until legal full text is hydrated and the Independent Reviewer completes seven structured overlap dimensions for each dangerous prior, the only valid novelty result is `NOVELTY_UNCERTAIN`.

- Hardened Scout retrieval run: `2b8e1962-fa11-444e-87f3-85870196e609`
- Hardened Reviewer retrieval run: `3b0a7d8b-ab8e-4f11-8a83-8e243e8d0b16`
- Known dangerous priors found: 5/5
- Deep-audit set: 30 papers
- Legal full-text/source-span status for the five mandatory priors: `FULL_TEXT_UNAVAILABLE`
- Structured decision: `NOVELTY_UNCERTAIN`
- Decision reason: A dangerous prior lacks legal full text or source spans.

## Data finding

Official DROID documentation reports a 1.7 TB RLDS full dataset and a 2 GB, 100-episode debug subset. The documented schema exposes observations, actions, and language instructions; it does not establish a closed-loop failure/intervention target label. Homepage reachability is therefore not DATA_READY. The previous claim remains `DATA_LABEL_GAP` unless a legitimate derived label is defined and independently reviewed.
