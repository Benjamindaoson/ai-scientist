from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

from benchmarks.core.benchmark import ResearchBenchmark


class CIFAR10CBenchmark(ResearchBenchmark):
    name = "cifar10c"
    url = "https://zenodo.org/records/2535967/files/CIFAR-10-C.tar?download=1"
    expected_size_bytes = 2_900_000_000

    def __init__(self, root="data/cifar10c"):
        self.root = Path(root)
        self.archive = self.root / "CIFAR-10-C.tar"

    def load(self):
        if not self.archive.exists():
            raise FileNotFoundError(f"CIFAR-10-C is not downloaded: {self.archive}")
        return self.archive

    def download(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(self.url, timeout=60) as response, self.archive.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
        return self.archive

    def checksum(self):
        digest = hashlib.md5()
        with self.archive.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def evaluate(self, predictions, targets):
        from .evaluator import evaluate_cifar10c
        return evaluate_cifar10c(predictions, targets)
