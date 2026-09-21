from __future__ import annotations


def evaluate_cifar10c(clean_predictions, corruption_predictions, targets, corruption_errors=None):
    clean_accuracy = sum(a == b for a, b in zip(clean_predictions, targets)) / len(targets)
    corruption_accuracy = sum(a == b for a, b in zip(corruption_predictions, targets)) / len(targets)
    errors = corruption_errors or [1.0 - corruption_accuracy]
    return {
        "clean_accuracy": clean_accuracy,
        "corruption_accuracy": corruption_accuracy,
        "mce": sum(errors) / len(errors),
    }
