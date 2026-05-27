"""Tests for the regression-helper machinery (``tests/_regression_helpers.py``).

The helper is shared by regression tests that pin a published reference
fit (currently ``test_valentin_eth_regression.py``, future ones to come).
These tests cover the comparison logic itself — they don't need real data.
"""

from __future__ import annotations


import pytest

from tests._regression_helpers import (
    RegressionReference,
    assert_summary_matches_reference,
    env_csv_path,
)

# ---------------------------------------------------------------------------
# env_csv_path
# ---------------------------------------------------------------------------


def test_env_csv_path_unset_returns_none(monkeypatch):
    monkeypatch.delenv("X_TEST_VAR", raising=False)
    assert env_csv_path("X_TEST_VAR") is None


def test_env_csv_path_set_but_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("X_TEST_VAR", str(tmp_path / "nope.csv"))
    assert env_csv_path("X_TEST_VAR") is None


def test_env_csv_path_set_and_exists_returns_path(monkeypatch, tmp_path):
    f = tmp_path / "ok.csv"
    f.write_text("a,b\n1,2\n")
    monkeypatch.setenv("X_TEST_VAR", str(f))
    out = env_csv_path("X_TEST_VAR")
    assert out == f


# ---------------------------------------------------------------------------
# assert_summary_matches_reference — numeric fields
# ---------------------------------------------------------------------------


def _ref(**summary) -> RegressionReference:
    return RegressionReference(summary=summary, rel_tol=0.05, iter_range=(50, 300))


def test_numeric_within_tolerance_passes():
    ref = _ref(log_likelihood=-100.0, bic=200.0)
    assert_summary_matches_reference(
        {"log_likelihood": -101.0, "bic": 195.0}, ref
    )  # 1% / 2.5% drifts both within 5%


def test_numeric_outside_tolerance_fails():
    ref = _ref(log_likelihood=-100.0)
    with pytest.raises(AssertionError, match="log_likelihood.*tol 5%"):
        assert_summary_matches_reference({"log_likelihood": -120.0}, ref)


def test_per_field_tol_overrides_default():
    ref = RegressionReference(
        summary={"log_likelihood": -100.0},
        rel_tol=0.50,
        per_field_tol={"log_likelihood": 0.01},
    )
    # 5% drift fails because per-field tol is 1%
    with pytest.raises(AssertionError, match="tol 1%"):
        assert_summary_matches_reference({"log_likelihood": -105.0}, ref)


def test_zero_reference_uses_abs_tolerance():
    ref = _ref(bic=0.0)
    # Default rel_tol 0.05 reinterpreted as abs tol since ref is exactly 0
    assert_summary_matches_reference({"bic": 0.04}, ref)
    with pytest.raises(AssertionError, match="bic.*expected ~0"):
        assert_summary_matches_reference({"bic": 0.1}, ref)


# ---------------------------------------------------------------------------
# assert_summary_matches_reference — booleans, strings, None
# ---------------------------------------------------------------------------


def test_boolean_exact_match():
    ref = _ref(converged=True)
    assert_summary_matches_reference({"converged": True}, ref)
    with pytest.raises(AssertionError, match="converged.*exact match"):
        assert_summary_matches_reference({"converged": False}, ref)


def test_string_exact_match():
    ref = _ref(emission_type="gaussian")
    assert_summary_matches_reference({"emission_type": "gaussian"}, ref)
    with pytest.raises(AssertionError, match="emission_type.*exact match"):
        assert_summary_matches_reference({"emission_type": "gmm"}, ref)


def test_none_field_must_be_none():
    ref = _ref(n_mix=None)
    assert_summary_matches_reference({"n_mix": None}, ref)
    with pytest.raises(AssertionError, match="n_mix.*expected None"):
        assert_summary_matches_reference({"n_mix": 3}, ref)


# ---------------------------------------------------------------------------
# assert_summary_matches_reference — n_iter_actual special case
# ---------------------------------------------------------------------------


def test_n_iter_within_explicit_range():
    ref = _ref(n_iter_actual=100)  # iter_range=(50, 300) from _ref
    assert_summary_matches_reference({"n_iter_actual": 75}, ref)
    assert_summary_matches_reference({"n_iter_actual": 250}, ref)


def test_n_iter_outside_explicit_range_fails():
    ref = _ref(n_iter_actual=100)
    with pytest.raises(AssertionError, match=r"n_iter_actual.*\[50, 300\]"):
        assert_summary_matches_reference({"n_iter_actual": 400}, ref)


def test_n_iter_default_factor_range():
    """Without explicit iter_range, falls back to [ref/factor, ref*factor]."""
    ref = RegressionReference(
        summary={"n_iter_actual": 100},
        iter_range_factor=2,  # → [50, 200]
    )
    assert_summary_matches_reference({"n_iter_actual": 199}, ref)
    with pytest.raises(AssertionError, match=r"n_iter_actual.*\[50, 200\]"):
        assert_summary_matches_reference({"n_iter_actual": 201}, ref)


# ---------------------------------------------------------------------------
# Error path : missing key
# ---------------------------------------------------------------------------


def test_missing_actual_key_raises_clearly():
    ref = _ref(log_likelihood=-100.0, bic=200.0)
    with pytest.raises(AssertionError, match="reference key 'bic' missing"):
        assert_summary_matches_reference({"log_likelihood": -101.0}, ref)
