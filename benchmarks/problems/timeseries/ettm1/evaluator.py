from __future__ import annotations

from itertools import chain


def evaluate_forecasts(predictions, targets) -> dict[str, float]:
    predicted = list(chain.from_iterable(predictions))
    actual = list(chain.from_iterable(targets))
    if not predicted or len(predicted) != len(actual):
        raise ValueError("predictions and targets must have the same non-empty size")
    errors = [prediction - target for prediction, target in zip(predicted, actual)]
    return {
        "mse": sum(error * error for error in errors) / len(errors),
        "mae": sum(abs(error) for error in errors) / len(errors),
    }
