import numpy as np

from benchmarks.baselines.timeseries.dlinear import DLinear, DLinearConfig


def test_dlinear_returns_horizon_and_channel_dimensions():
    model = DLinear(DLinearConfig(seq_len=8, pred_len=3, channels=2, moving_avg=3))
    output = model.predict(np.ones((4, 8, 2)))

    assert output.shape == (4, 3, 2)


def test_dlinear_moving_average_changes_two_branch_model():
    rng = np.random.default_rng(7)
    inputs = rng.normal(size=(12, 8, 2))
    targets = rng.normal(size=(12, 4, 2))
    short = DLinear(DLinearConfig(seq_len=8, pred_len=4, channels=2, moving_avg=1)).fit(inputs, targets)
    long = DLinear(DLinearConfig(seq_len=8, pred_len=4, channels=2, moving_avg=7)).fit(inputs, targets)
    assert not np.allclose(short.predict(inputs), long.predict(inputs))
