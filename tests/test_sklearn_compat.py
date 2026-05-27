"""Tests for the sklearn-compatible HMMClassifier (Phase I.2).

Coverage :
    - Basic fit / predict / predict_proba / score on standard data
    - Supervised mode via ``y`` argument
    - sklearn protocol : get_params / set_params / clone
    - Drop-in with sklearn.pipeline.Pipeline
    - Drop-in with sklearn.model_selection.GridSearchCV
    - Drop-in with cross_val_score (TimeSeriesSplit for HMM semantics)
    - Fitted attribute conventions
    - _repr_html_ before and after fit
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from hmm_core.sklearn_compat import HMMClassifier

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_regime_data():
    """Two well-separated Gaussian regimes : easy to fit, easy to verify."""
    rng = np.random.default_rng(42)
    X = np.concatenate(
        [
            rng.normal(0.0, 0.5, (80, 1)),
            rng.normal(5.0, 0.5, (80, 1)),
            rng.normal(0.0, 0.5, (80, 1)),
            rng.normal(5.0, 0.5, (80, 1)),
        ]
    )
    # True labels (alternating)
    y = np.concatenate([np.zeros(80), np.ones(80), np.zeros(80), np.ones(80)]).astype(int)
    return X, y


# ---------------------------------------------------------------------------
# Basic API
# ---------------------------------------------------------------------------


def test_hmm_classifier_basic_unsupervised_fit_predict(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=50)
    clf.fit(X)
    assert hasattr(clf, "transmat_")
    assert clf.transmat_.shape == (2, 2)
    states = clf.predict(X)
    assert states.shape == (len(X),)
    assert set(np.unique(states)).issubset({0, 1})


def test_hmm_classifier_predict_proba_returns_correct_shape(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=30).fit(X)
    posteriors = clf.predict_proba(X)
    assert posteriors.shape == (len(X), 2)
    np.testing.assert_allclose(posteriors.sum(axis=1), 1.0, atol=1e-9)


def test_hmm_classifier_supervised_fit(two_regime_data):
    """When y is provided, supervised fit (closed-form) is used."""
    X, y = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=10).fit(X, y)
    assert clf.converged_ is True  # supervised always "converges" in one pass
    assert clf.n_iter_ == 1


def test_hmm_classifier_score_with_labels_returns_accuracy(two_regime_data):
    X, y = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=10).fit(X, y)
    acc = clf.score(X, y)
    # Supervised fit on clean data should give near-perfect accuracy
    assert 0.9 <= acc <= 1.0


def test_hmm_classifier_score_without_labels_returns_log_likelihood(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=30).fit(X)
    log_lik_per_timestep = clf.score(X)
    # Should be a finite negative-ish float
    assert np.isfinite(log_lik_per_timestep)


# ---------------------------------------------------------------------------
# sklearn protocol : get_params / set_params / clone
# ---------------------------------------------------------------------------


def test_get_params_returns_all_constructor_args():
    clf = HMMClassifier(n_states=4, n_iter=50, tol=1e-5)
    params = clf.get_params()
    expected = {
        "n_states",
        "emission_type",
        "covariance_type",
        "n_features",
        "n_mix",
        "n_symbols",
        "allowed_transitions",
        "startprob",
        "init_strategy",
        "init_seed",
        "n_iter",
        "tol",
    }
    assert set(params.keys()) == expected
    assert params["n_states"] == 4
    assert params["n_iter"] == 50


def test_set_params_modifies_estimator():
    clf = HMMClassifier(n_states=2)
    clf.set_params(n_states=5, init_seed=123)
    assert clf.n_states == 5
    assert clf.init_seed == 123


def test_clone_produces_unfitted_equivalent(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=3, n_iter=20).fit(X)
    cloned = clone(clf)
    # clone() produces a fresh unfitted estimator with same params
    assert not hasattr(cloned, "result_")
    assert cloned.get_params() == clf.get_params()
    # Should be re-fittable
    cloned.fit(X)
    assert hasattr(cloned, "transmat_")


# ---------------------------------------------------------------------------
# sklearn.pipeline.Pipeline integration
# ---------------------------------------------------------------------------


def test_hmm_classifier_in_sklearn_pipeline(two_regime_data):
    X, y = two_regime_data
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("hmm", HMMClassifier(n_states=2, n_iter=30)),
        ]
    )
    pipe.fit(X, y)
    states = pipe.predict(X)
    assert states.shape == (len(X),)


def test_hmm_classifier_pipeline_supervised_accuracy(two_regime_data):
    X, y = two_regime_data
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("hmm", HMMClassifier(n_states=2, n_iter=10)),
        ]
    )
    pipe.fit(X, y)
    acc = pipe.score(X, y)
    assert acc >= 0.9


# ---------------------------------------------------------------------------
# sklearn.model_selection.GridSearchCV
# ---------------------------------------------------------------------------


def test_hmm_classifier_in_grid_search(two_regime_data):
    """Grid search over n_states + init_strategy."""
    X, y = two_regime_data
    param_grid = {
        "n_states": [2, 3],
        "init_strategy": ["kmeans", "uniform"],
    }
    clf = HMMClassifier(n_iter=10)
    # Use a simple split for speed ; HMMs aren't iid so KFold here is purely
    # mechanical.
    search = GridSearchCV(clf, param_grid, cv=2, scoring="accuracy")
    search.fit(X, y)
    assert search.best_params_ is not None
    # Best should be n_states=2 (the true number)
    assert search.best_params_["n_states"] == 2


# ---------------------------------------------------------------------------
# cross_val_score
# ---------------------------------------------------------------------------


def test_hmm_classifier_cross_val_score(two_regime_data):
    """cross_val_score with TimeSeriesSplit (HMM-appropriate)."""
    X, y = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=10)
    scores = cross_val_score(clf, X, y, cv=TimeSeriesSplit(n_splits=3))
    # Should produce 3 scores, all finite
    assert scores.shape == (3,)
    assert np.all(np.isfinite(scores))


# ---------------------------------------------------------------------------
# Fitted attribute conventions
# ---------------------------------------------------------------------------


def test_fitted_attributes_follow_sklearn_convention(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=20).fit(X)
    # All fitted attrs end with _
    for attr in [
        "transmat_",
        "startprob_",
        "classes_",
        "n_iter_",
        "log_likelihood_",
        "bic_",
        "aic_",
        "converged_",
        "n_features_in_",
    ]:
        assert hasattr(clf, attr), f"missing fitted attribute : {attr}"


def test_classes_is_arange_n_states(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=3, n_iter=10).fit(X)
    np.testing.assert_array_equal(clf.classes_, np.arange(3))


def test_n_features_in_matches_input(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=10).fit(X)
    assert clf.n_features_in_ == X.shape[1]


# ---------------------------------------------------------------------------
# Rich display (_repr_html_)
# ---------------------------------------------------------------------------


def test_repr_html_before_fit_shows_params():
    clf = HMMClassifier(n_states=5, init_seed=99)
    html = clf._repr_html_()
    assert isinstance(html, str) and len(html) > 50
    assert "not fitted" in html.lower()
    assert "n_states" in html


def test_repr_html_after_fit_delegates_to_fitted_model(two_regime_data):
    X, _ = two_regime_data
    clf = HMMClassifier(n_states=2, n_iter=10).fit(X)
    html = clf._repr_html_()
    assert "Log-likelihood" in html  # from FittedModel._repr_html_


# ---------------------------------------------------------------------------
# Multinomial emission integration (no covariance_type)
# ---------------------------------------------------------------------------


def test_multinomial_classifier():
    rng = np.random.default_rng(0)
    X = rng.integers(0, 4, size=(200, 1))
    clf = HMMClassifier(n_states=2, emission_type="multinomial", n_symbols=4, n_iter=20)
    clf.fit(X)
    states = clf.predict(X)
    assert states.shape == (200,)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_predict_before_fit_raises():
    from sklearn.exceptions import NotFittedError

    clf = HMMClassifier(n_states=2)
    with pytest.raises(NotFittedError):
        clf.predict(np.array([[1.0], [2.0]]))


def test_1d_input_is_reshaped_automatically(two_regime_data):
    """sklearn convention : 2D input. We accept 1D and reshape."""
    X, _ = two_regime_data
    X_1d = X.ravel()
    clf = HMMClassifier(n_states=2, n_iter=10)
    clf.fit(X_1d)
    states = clf.predict(X_1d)
    assert states.shape == (len(X_1d),)
