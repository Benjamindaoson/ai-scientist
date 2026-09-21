from __future__ import annotations

import numpy as np


class _LinearClassifier:
    def fit(self, x, y):
        x = np.c_[np.ones(len(x)), x]
        self.weights = np.linalg.pinv(x) @ y
        return self

    def predict_proba(self, x):
        logits = np.c_[np.ones(len(x)), x] @ self.weights
        return 1 / (1 + np.exp(-np.clip(logits, -40, 40)))


class XGBoostBaseline(_LinearClassifier):
    implementation = "numpy_fallback_for_xgboost"


class MLPBaseline(_LinearClassifier):
    implementation = "numpy_fallback_for_mlp"
