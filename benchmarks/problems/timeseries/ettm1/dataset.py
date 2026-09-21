from __future__ import annotations

import csv
import statistics
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ETTM1_URL = "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTm1.csv"
FEATURES = ("HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT")


@dataclass(frozen=True)
class Window:
    inputs: list[list[float]]
    targets: list[list[float]]


class ETTm1Dataset:
    """Real ETTm1 CSV adapter with chronological splits and normalized windows."""

    def __init__(
        self,
        root: str | Path = "data/ettm1",
        lookback: int = 96,
        horizon: int = 96,
        split_points: tuple[int, int] = (34560, 46080),
        download: bool = True,
        url: str = ETTM1_URL,
    ):
        self.root = Path(root)
        self.lookback = lookback
        self.horizon = horizon
        self.split_points = split_points
        self.url = url
        self.path = self.root / "ETTm1.csv"
        if download and not self.path.exists():
            self.download()
        self.rows = self._read_rows()
        self.means, self.stdevs = self._fit_scaler(self.rows[: self.split_points[0]])

    def download(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(self.url, timeout=60) as response:
            self.path.write_bytes(response.read())
        return self.path

    def _read_rows(self) -> list[list[float]]:
        if not self.path.exists():
            raise FileNotFoundError(f"ETTm1 data not found: {self.path}")
        with self.path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = [field for field in FEATURES if field not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"ETTm1 CSV missing columns: {missing}")
            rows = [[float(row[field]) for field in FEATURES] for row in reader]
        if len(rows) <= self.split_points[1]:
            raise ValueError("ETTm1 CSV is shorter than the configured train/validation split")
        return rows

    @staticmethod
    def _fit_scaler(rows: list[list[float]]) -> tuple[list[float], list[float]]:
        columns = list(zip(*rows))
        means = [statistics.fmean(column) for column in columns]
        stdevs = [statistics.pstdev(column) or 1.0 for column in columns]
        return means, stdevs

    def _normalize(self, row: list[float]) -> list[float]:
        return [(value - mean) / stdev for value, mean, stdev in zip(row, self.means, self.stdevs)]

    def split_bounds(self, split: str) -> tuple[int, int]:
        train_end, validation_end = self.split_points
        bounds = {"train": (0, train_end), "val": (train_end, validation_end), "test": (validation_end, len(self.rows))}
        try:
            return bounds[split]
        except KeyError as exc:
            raise ValueError(f"unknown ETTm1 split: {split}") from exc

    def split_lengths(self) -> dict[str, int]:
        return {split: end - start for split in ("train", "val", "test") for start, end in [self.split_bounds(split)]}

    def windows(self, split: str = "train"):
        start, end = self.split_bounds(split)
        first = start + self.lookback
        last = end - self.horizon
        normalized = [self._normalize(row) for row in self.rows]
        for target_start in range(first, last + 1):
            yield Window(
                inputs=normalized[target_start - self.lookback : target_start],
                targets=normalized[target_start : target_start + self.horizon],
            )

    def batches(self, split: str = "train", batch_size: int = 32):
        batch: list[Window] = []
        for window in self.windows(split):
            batch.append(window)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
