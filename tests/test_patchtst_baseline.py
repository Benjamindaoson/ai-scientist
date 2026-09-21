import numpy as np

from benchmarks.baselines.timeseries.patchtst import PatchTST, PatchTSTConfig


def test_patchtst_returns_horizon_and_channel_dimensions():
    model = PatchTST(PatchTSTConfig(seq_len=8, pred_len=3, channels=2, patch_len=4, stride=2))
    output = model.predict(np.ones((4, 8, 2)))

    assert output.shape == (4, 3, 2)
