"""Real ML benchmark problem adapters."""
from .timeseries.problem import TIME_SERIES_PROBLEM, TimeSeriesProblem
from .robustness.problem import ROBUSTNESS_PROBLEM, RobustnessProblem
from .tableshift.problem import TABLESHIFT_PROBLEM, TableShiftProblem

__all__ = [
    "TIME_SERIES_PROBLEM", "TimeSeriesProblem",
    "ROBUSTNESS_PROBLEM", "RobustnessProblem",
    "TABLESHIFT_PROBLEM", "TableShiftProblem",
]
