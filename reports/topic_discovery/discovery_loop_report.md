# Autonomous Discovery Loop Report

## Runs

```json
[
  {
    "discovery_run_id": "54ad4ad7-c499-42b0-aeca-c17b25f65c33",
    "program": {
      "name": "Embodied Intelligence Topic Discovery",
      "domains": [
        "Embodied AI",
        "Robot Learning",
        "Vision-Language-Action",
        "World Models",
        "Multimodal Agents",
        "Agentic Robotics"
      ],
      "adjacent_domains": [
        "machine learning",
        "computer vision",
        "reinforcement learning",
        "control",
        "multimodal learning",
        "NLP/agents"
      ],
      "candidate_batch_size": 20
    },
    "status": "TOPIC_READY",
    "wave": 1,
    "counts": {
      "ideas_killed": 0,
      "ideas_generated": 20
    },
    "current_strategy": null,
    "topic_id": "e23964c7-7a28-4301-a264-a866dca53634",
    "error": null,
    "started_at": "2026-09-28 05:37:06.573696+00:00",
    "completed_at": "2026-09-28 05:37:27.310344+00:00"
  }
]
```

## Candidate and audit outcomes

- Candidate states: `{"TOPIC_READY": 1, "CANDIDATE": 19}`
- Lineage states: `{"TOPIC_READY": 1, "CANDIDATE": 19}`
- Ideas reframed: 0
- Feasibility-killed: 0
- Final-review-killed: 0
- Novelty audits (including uncertain and survived): `[{"actor_role": "reviewer", "decision": "NOVELTY_SURVIVES_AUDIT", "count": 1}, {"actor_role": "scout", "decision": "NOVELTY_SURVIVES_AUDIT", "count": 1}]`

A failed candidate or wave is not a terminal condition. The loop changes strategy across CFP themes, workshop questions, limitations/contradictions, measurement/identification, cross-domain transfer, and new capabilities. Manuscript and full experiment paths are not invoked.
