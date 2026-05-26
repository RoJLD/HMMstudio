"""scikit-learn compatible wrappers for hmm-studio (Phase I.2).

Drop hmm-studio models into any existing scikit-learn workflow :

    >>> from sklearn.pipeline import Pipeline
    >>> from sklearn.preprocessing import StandardScaler
    >>> from hmm_core.sklearn_compat import HMMClassifier
    >>>
    >>> pipe = Pipeline([
    ...     ("scaler", StandardScaler()),
    ...     ("hmm", HMMClassifier(n_states=3, emission_type="gaussian")),
    ... ])
    >>> pipe.fit(X, y)
    >>> pipe.score(X_test, y_test)

Compatible with :
- ``sklearn.pipeline.Pipeline``
- ``sklearn.model_selection.GridSearchCV`` / ``RandomizedSearchCV``
- ``sklearn.model_selection.cross_val_score``
- ``sklearn.base.clone``
- ``sklearn.metrics`` (any classification metric on predictions)

This is Phase I.2 of the hybrid distribution strategy (ADR-0012). The
HMM math stays in ``hmm_core.fit`` / ``hmm_core.nhmm`` ; this module is
purely a thin wrapper exposing the scikit-learn contract.
"""

from __future__ import annotations

from hmm_core.sklearn_compat.classifier import HMMClassifier

__all__ = ["HMMClassifier"]
