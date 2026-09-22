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


class TorchDLinear:
    """Reference two-branch DLinear backend used when PyTorch is available."""

    def __init__(self, config: DLinearConfig, seed: int = 1, epochs: int = 20, learning_rate: float = 1e-3):
        import torch
        from torch import nn

        torch.manual_seed(seed)
        self.config = config
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.seasonal = nn.Linear(config.seq_len, config.pred_len).to(self.device)
        self.trend = nn.Linear(config.seq_len, config.pred_len).to(self.device)

    def _decompose(self, values):
        import torch.nn.functional as F

        radius = self.config.moving_avg // 2
        channels_first = values.transpose(1, 2)
        trend = F.avg_pool1d(F.pad(channels_first, (radius, radius), mode="replicate"), self.config.moving_avg, stride=1)
        return (channels_first - trend).transpose(1, 2), trend.transpose(1, 2)

    def fit(self, inputs: np.ndarray, targets: np.ndarray) -> "TorchDLinear":
        import torch
        import torch.nn.functional as F

        x = torch.as_tensor(inputs, dtype=torch.float32, device=self.device)
        y = torch.as_tensor(targets, dtype=torch.float32, device=self.device)
        optimizer = torch.optim.Adam(list(self.seasonal.parameters()) + list(self.trend.parameters()), lr=self.learning_rate)
        for _ in range(self.epochs):
            seasonal, trend = self._decompose(x)
            prediction = self.seasonal(seasonal.transpose(1, 2)).transpose(1, 2) + self.trend(trend.transpose(1, 2)).transpose(1, 2)
            loss = F.mse_loss(prediction, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        return self

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        import torch

        with torch.no_grad():
            x = torch.as_tensor(inputs, dtype=torch.float32, device=self.device)
            seasonal, trend = self._decompose(x)
            prediction = self.seasonal(seasonal.transpose(1, 2)).transpose(1, 2) + self.trend(trend.transpose(1, 2)).transpose(1, 2)
        return prediction.cpu().numpy()
