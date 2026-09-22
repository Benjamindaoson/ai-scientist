from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DLinearConfig:
    seq_len: int = 96
    pred_len: int = 96
    channels: int = 7
    moving_avg: int = 25


class DLinear:
    """Dependency-light DLinear inference model.

    The decomposition and per-channel linear heads follow DLinear's published
    design. ``fit`` estimates the heads with least squares for local CPU runs;
    a Torch implementation can replace this adapter without changing runners.
    """

    def __init__(self, config: DLinearConfig):
        if config.moving_avg < 1 or config.moving_avg % 2 == 0:
            raise ValueError("moving_avg must be a positive odd integer")
        self.config = config
        self.seasonal_weights = np.zeros((config.channels, config.seq_len, config.pred_len), dtype=float)
        self.trend_weights = np.zeros((config.channels, config.seq_len, config.pred_len), dtype=float)

    def _moving_average(self, values: np.ndarray) -> np.ndarray:
        radius = self.config.moving_avg // 2
        padded = np.pad(values, ((0, 0), (radius, radius), (0, 0)), mode="edge")
        output = np.empty_like(values, dtype=float)
        for index in range(values.shape[1]):
            output[:, index, :] = padded[:, index : index + self.config.moving_avg, :].mean(axis=1)
        return output

    def _decompose(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        trend = self._moving_average(values)
        return values - trend, trend

    def fit(self, inputs: np.ndarray, targets: np.ndarray) -> "DLinear":
        seasonal, trend = self._decompose(inputs)
        for channel in range(self.config.channels):
            self.seasonal_weights[channel] = np.linalg.pinv(seasonal[:, :, channel]) @ targets[:, :, channel]
            self.trend_weights[channel] = np.linalg.pinv(trend[:, :, channel]) @ targets[:, :, channel]
        return self

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        values = np.asarray(inputs, dtype=float)
        if values.ndim != 3 or values.shape[1:] != (self.config.seq_len, self.config.channels):
            raise ValueError("inputs must have shape [batch, seq_len, channels]")
        seasonal, trend = self._decompose(values)
        return np.stack(
            [
                seasonal[:, :, channel] @ self.seasonal_weights[channel]
                + trend[:, :, channel] @ self.trend_weights[channel]
                for channel in range(self.config.channels)
            ],
            axis=-1,
        )
