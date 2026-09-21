from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from pathlib import Path

from benchmarks.core.benchmark import ResearchBenchmark


URL = "https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip"


class DiabetesReadmission(ResearchBenchmark):
    name = "diabetes_readmission"

    def __init__(self, root="data/tableshift"):
        self.root = Path(root)
        self.csv_path = self.root / "diabetic_data.csv"

    def download(self):
        self.root.mkdir(parents=True, exist_ok=True)
        payload = urllib.request.urlopen(URL, timeout=60).read()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            member = next(name for name in archive.namelist() if name.endswith("diabetic_data.csv"))
            self.csv_path.write_bytes(archive.read(member))
        return self.csv_path

    def load(self):
        if not self.csv_path.exists():
            self.download()
        with self.csv_path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def setup(self):
        rows = self.load()
        target = [int(row["readmitted"] != "NO") for row in rows]
        domains = [row.get("admission_source_id", "") for row in rows]
        return rows, target, domains

    def evaluate(self, predictions, targets):
        from .evaluator import evaluate_tableshift
        return evaluate_tableshift(predictions, targets)
