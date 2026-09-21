from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PatchTSTConfig:
    seq_len: int = 96
    pred_len: int = 96
    channels: int = 7
    patch_len: int = 16
    stride: int = 8


class PatchTST:
    """Patch-based channel-independent forecasting fallback.

    It preserves PatchTST's patch tokenization contract and uses NumPy least
    squares when the PyTorch implementation is unavailable in the environment.
    """

    def __init__(self, config: PatchTSTConfig):
        if config.patch_len <= 0 or config.stride <= 0:
            raise ValueError("patch_len and stride must be positive")
        if config.patch_len > config.seq_len:
            raise ValueError("patch_len cannot exceed seq_len")
        self.config = config
        self.patch_count = 1 + (config.seq_len - config.patch_len) // config.stride
        feature_count = self.patch_count * config.patch_len
        self.weights = np.zeros((config.channels, feature_count, config.pred_len), dtype=float)

    def _patches(self, inputs: np.ndarray) -> np.ndarray:
        values = np.asarray(inputs, dtype=float)
        if values.ndim != 3 or values.shape[1:] != (self.config.seq_len, self.config.channels):
            raise ValueError("inputs must have shape [batch, seq_len, channels]")
        patches = [
            values[:, start : start + self.config.patch_len, :]
            for start in range(0, self.config.seq_len - self.config.patch_len + 1, self.config.stride)
        ]
        return np.concatenate(patches, axis=1)

    def fit(self, inputs: np.ndarray, targets: np.ndarray) -> "PatchTST":
        features = self._patches(inputs)
        for channel in range(self.config.channels):
            self.weights[channel] = np.linalg.pinv(features[:, :, channel]) @ targets[:, :, channel]
        return self

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        features = self._patches(inputs)
        return np.stack(
            [features[:, :, channel] @ self.weights[channel] for channel in range(self.config.channels)],
            axis=-1,
        )
