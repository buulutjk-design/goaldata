# tests/test_analysis.py
import pytest
from analysis import evaluate_match

def test_evaluate_match_basic():
    item = {"lig":"Test","home":"A","away":"B","lambda_h":1.8,"lambda_a":0.9,"ml_p":0.8,"lig_gol_index":1.0}
    res = evaluate_match(item, n_sim=1000)
    assert res is not None
    assert "p" in res
    assert 0.0 <= res["p"] <= 1.0
