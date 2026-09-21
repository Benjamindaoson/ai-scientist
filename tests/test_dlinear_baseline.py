import numpy as np

from benchmarks.baselines.timeseries.dlinear import DLinear, DLinearConfig


def test_dlinear_returns_horizon_and_channel_dimensions():
    model = DLinear(DLinearConfig(seq_len=8, pred_len=3, channels=2, moving_avg=3))
    output = model.predict(np.ones((4, 8, 2)))

    assert output.shape == (4, 3, 2)
