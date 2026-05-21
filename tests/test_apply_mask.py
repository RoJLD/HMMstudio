"""Tests for the mask-and-renormalize utility."""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.fit._base import _apply_mask


def test_zeros_preserved_on_forbidden_edges():
    A = np.array([[0.5, 0.3, 0.2],
                  [0.1, 0.7, 0.2],
                  [0.3, 0.3, 0.4]])
    mask = np.array([[True, True, False],
                     [False, True, True],
                     [True, False, True]])
    result = _apply_mask(A, mask)
    assert result[0, 2] == 0.0
    assert result[1, 0] == 0.0
    assert result[2, 1] == 0.0


def test_rows_sum_to_one():
    A = np.array([[0.5, 0.3, 0.2],
                  [0.1, 0.7, 0.2],
                  [0.3, 0.3, 0.4]])
    mask = np.array([[True, True, False],
                     [False, True, True],
                     [True, False, True]])
    result = _apply_mask(A, mask)
    np.testing.assert_allclose(result.sum(axis=1), 1.0, atol=1e-12)


def test_no_constraint_when_all_true():
    A = np.array([[0.5, 0.3, 0.2],
                  [0.1, 0.7, 0.2]])
    mask = np.ones((2, 3), dtype=bool)
    result = _apply_mask(A, mask)
    np.testing.assert_allclose(result, A, atol=1e-12)


def test_row_with_zero_allowed_falls_back_to_uniform_on_mask():
    # Row 0 is entirely zero after masking (A * mask gives 0). Mask has 2
    # allowed edges in that row. Fallback should put 0.5 on each allowed.
    A = np.array([[0.0, 0.0, 1.0],
                  [0.3, 0.3, 0.4]])
    mask = np.array([[True, True, False],
                     [True, True, True]])
    with pytest.warns(UserWarning, match="falling back to uniform"):
        result = _apply_mask(A, mask)
    assert result[0, 0] == pytest.approx(0.5)
    assert result[0, 1] == pytest.approx(0.5)
    assert result[0, 2] == 0.0
    np.testing.assert_allclose(result.sum(axis=1), 1.0, atol=1e-12)


def test_row_with_completely_empty_mask_raises():
    # Mask row entirely False = no allowed edges. Impossible to renormalize.
    A = np.array([[0.5, 0.3, 0.2]])
    mask = np.array([[False, False, False]])
    with pytest.raises(ValueError, match="empty mask row"):
        _apply_mask(A, mask)


def test_shape_mismatch_raises():
    A = np.ones((2, 3))
    mask = np.ones((2, 2), dtype=bool)
    with pytest.raises(ValueError, match="shape mismatch"):
        _apply_mask(A, mask)
