from __future__ import annotations

import math


def _auroc(scores, targets):
    pairs = sorted(zip(scores, targets), reverse=True)
    positives = sum(targets)
    negatives = len(targets) - positives
    if not positives or not negatives:
        return float("nan")
    rank_sum = sum(index + 1 for index, (_, target) in enumerate(sorted(zip(scores, targets))) if target)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def evaluate_tableshift(id_scores, ood_scores, targets, ood_targets=None):
    id_auc = _auroc(id_scores, targets)
    ood_auc = _auroc(ood_scores, ood_targets if ood_targets is not None else targets)
    return {"id_auroc": id_auc, "ood_auroc": ood_auc, "ood_gap": id_auc - ood_auc if not math.isnan(id_auc + ood_auc) else float("nan")}
