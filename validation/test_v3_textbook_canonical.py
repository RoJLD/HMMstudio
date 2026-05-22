"""V.3 — Reproduce canonical textbook problems with known analytical answers.

These tests pin our implementation against established academic references.
When a reviewer asks "how do you know your Viterbi is correct?", we point
here.

Each test :
    1. Builds a canonical HMM topology from a published reference
    2. Loads the canonical observation sequence
    3. Runs inference (forward-backward or Viterbi)
    4. Asserts agreement with published numerical values (or the
       analytically-derived reference computed in this file's docstring)

We DO NOT fit anything in V.3 — these tests validate inference on
known-correct parameters, isolated from any EM-related concerns.
"""

from __future__ import annotations

import numpy as np
import pytest

from hmm_core.fit.multinomial import ConstrainedMultinomialHMM


# ---------------------------------------------------------------------------
# V.3.1 — Russell & Norvig umbrella world (AIMA, Chap. 14)
# ---------------------------------------------------------------------------


def _build_umbrella_model() -> ConstrainedMultinomialHMM:
    """Build the canonical umbrella HMM from AIMA Section 14.2.

    Hidden states : rain (0), sun (1)
    Observations  : no_umbrella (0), umbrella (1)

    Parameters fixed at the textbook values :
      P(rain_t | rain_{t-1}) = 0.7        P(sun_t | sun_{t-1}) = 0.7
      P(umbrella | rain)     = 0.9        P(umbrella | sun)    = 0.2
      P(rain_0)              = 0.5        P(sun_0)             = 0.5
    """
    model = ConstrainedMultinomialHMM(
        n_components=2,
        n_features=2,
        random_state=0,
        transmat_mask=None,
    )
    model.startprob_ = np.array([0.5, 0.5])
    model.transmat_ = np.array(
        [
            [0.7, 0.3],   # from rain : self=0.7, to sun=0.3
            [0.3, 0.7],   # from sun  : to rain=0.3, self=0.7
        ]
    )
    model.emissionprob_ = np.array(
        [
            [0.1, 0.9],   # rain : no_umb=0.1, umb=0.9
            [0.8, 0.2],   # sun  : no_umb=0.8, umb=0.2
        ]
    )
    return model


def test_v3_1_russell_norvig_umbrella_smoothing():
    """Reproduce AIMA Section 14.2.4 (smoothing) on the canonical 5-step sequence.

    Observation sequence : [umb, umb, no_umb, umb, umb] = [1, 1, 0, 1, 1].

    Expected smoothed posteriors P(R_t | x_{1:5}) (derived analytically
    via forward-backward on the model above, double-checked against AIMA
    figures) :

      t=1 : P(rain) ≈ 0.867
      t=2 : P(rain) ≈ 0.820
      t=3 : P(rain) ≈ 0.306    (after observing no_umbrella)
      t=4 : P(rain) ≈ 0.821
      t=5 : P(rain) ≈ 0.867

    Tolerance 5e-3 accommodates rounding from the 3-decimal expected values.
    """
    model = _build_umbrella_model()
    X = np.array([[1], [1], [0], [1], [1]])  # umbrella, umbrella, no, umbrella, umbrella

    posteriors = model.predict_proba(X)  # (T, K) smoothed
    p_rain = posteriors[:, 0]

    expected_p_rain = np.array([0.867, 0.820, 0.306, 0.821, 0.867])
    np.testing.assert_allclose(
        p_rain,
        expected_p_rain,
        atol=5e-3,
        err_msg=(
            f"AIMA umbrella smoothing mismatch :\n"
            f"  got      = {p_rain}\n"
            f"  expected = {expected_p_rain}"
        ),
    )


def test_v3_1b_russell_norvig_umbrella_filtering():
    """Reproduce the canonical AIMA filtering values for the same sequence.

    Filtering is P(R_t | x_{1:t}) — uses only the past. We compute it by
    running ``predict_proba`` on PREFIXES, taking the last entry each time.

    Expected filtered P(R_t) values from AIMA Section 14.2.2 :
      t=1 : 0.818
      t=2 : 0.883
      t=3 : 0.190
      t=4 : 0.731
      t=5 : 0.867
    """
    model = _build_umbrella_model()
    full_seq = np.array([[1], [1], [0], [1], [1]])

    expected_filtered = np.array([0.818, 0.883, 0.190, 0.731, 0.867])
    filtered = np.empty(5)
    for t in range(1, 6):
        prefix = full_seq[:t]
        posteriors = model.predict_proba(prefix)
        # predict_proba on prefix gives smoothed over the prefix ; the LAST
        # entry equals the filtered posterior at that time
        filtered[t - 1] = posteriors[-1, 0]

    np.testing.assert_allclose(
        filtered,
        expected_filtered,
        atol=5e-3,
        err_msg=(
            f"AIMA umbrella filtering mismatch :\n"
            f"  got      = {filtered}\n"
            f"  expected = {expected_filtered}"
        ),
    )


# ---------------------------------------------------------------------------
# V.3.2 — Durbin et al. dishonest casino
# ---------------------------------------------------------------------------


def _build_dishonest_casino() -> ConstrainedMultinomialHMM:
    """Build Durbin's dishonest casino model (Biological Sequence Analysis, Chap. 3).

    Hidden states : fair (0), loaded (1)
    Observations  : die faces 0..5 (i.e. 1..6 minus 1)

    Parameters fixed at the textbook values :
      P(stay in fair)   = 0.95          P(stay in loaded) = 0.90
      Fair emissions   : uniform 1/6 each face
      Loaded emissions : [0.1, 0.1, 0.1, 0.1, 0.1, 0.5] (loaded favors face 6 = index 5)
      Initial          : [0.5, 0.5]
    """
    model = ConstrainedMultinomialHMM(
        n_components=2,
        n_features=6,
        random_state=0,
        transmat_mask=None,
    )
    model.startprob_ = np.array([0.5, 0.5])
    model.transmat_ = np.array(
        [
            [0.95, 0.05],   # fair : stay 0.95, switch 0.05
            [0.10, 0.90],   # loaded : switch 0.10, stay 0.90
        ]
    )
    model.emissionprob_ = np.array(
        [
            [1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6, 1 / 6],   # fair : uniform
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.5],               # loaded : favors 6
        ]
    )
    return model


def test_v3_2_durbin_dishonest_casino_viterbi_accuracy(rng_seed):
    """On Durbin's dishonest casino, Viterbi must significantly beat the always-fair baseline.

    Strategy : sample T=1000 (X, Z) pairs from the canonical model, run our
    Viterbi decode, compare to the true sequence Z (with state-permutation
    invariance — try both labellings and take the best).

    Threshold = 0.70 :
    - Stationary distribution of (fair, loaded) is (2/3, 1/3) (from
      stationary equation π_fair · 0.05 = π_loaded · 0.10).
    - Naive "always-fair" predictor gets 2/3 ≈ 0.667 accuracy.
    - The dishonest casino is intrinsically hard to decode : loaded looks
      like fair most of the time, except on runs of face-6. Durbin Figure
      3.5 shows Viterbi catching most LONG loaded runs but missing short
      ones, giving ~70-80 % accuracy.
    - 0.70 is a robust threshold : significantly above baseline, achievable
      across seeds.
    """
    model = _build_dishonest_casino()
    T = 1000
    X, Z_true = model.sample(T, random_state=rng_seed)

    Z_pred = model.predict(X)
    acc_direct = float(np.mean(Z_pred == Z_true))
    acc_swap = float(np.mean(Z_pred == (1 - Z_true)))
    accuracy = max(acc_direct, acc_swap)

    # Above always-fair baseline of 2/3 + safety margin
    assert accuracy >= 0.70, (
        f"Durbin dishonest casino Viterbi accuracy = {accuracy:.3f} (< 0.70 threshold). "
        f"Direct alignment {acc_direct:.3f}, swapped {acc_swap:.3f}. "
        f"Baseline (always-fair) is ~0.667."
    )


def test_v3_2b_durbin_dishonest_casino_loaded_emission_skewed():
    """Sanity : conditional on Viterbi-decoded 'loaded' state, the proportion
    of face-6 must be visibly above 1/6 (≈ 0.5 by construction)."""
    model = _build_dishonest_casino()
    T = 5000
    X, _ = model.sample(T, random_state=123)
    Z_pred = model.predict(X)

    # Identify which Viterbi label corresponds to "loaded" — the one with the
    # higher proportion of face-5 (= face-6, since 0-indexed)
    face5_per_state = [
        np.mean(X[Z_pred == k, 0] == 5) if np.any(Z_pred == k) else 0.0
        for k in range(2)
    ]
    loaded_state = int(np.argmax(face5_per_state))

    p_face5_loaded = face5_per_state[loaded_state]
    assert p_face5_loaded > 0.35, (
        f"Decoded 'loaded' state has only {p_face5_loaded:.3f} of face-6 "
        f"(should be near 0.5 by construction)"
    )


# ---------------------------------------------------------------------------
# V.3.3 — Eisner ice cream HMM (Johns Hopkins / Jurafsky teaching example)
# ---------------------------------------------------------------------------


def _build_eisner_ice_cream() -> ConstrainedMultinomialHMM:
    """Build Eisner's ice cream HMM (canonical NLP teaching example).

    Hidden states : hot (0), cold (1) weather
    Observations  : number of ice creams eaten (1, 2, or 3) → 0-indexed 0, 1, 2

    Parameters (Jurafsky & Martin teaching slides) :
      P(hot_t | hot_{t-1})    = 0.7      P(cold_t | cold_{t-1}) = 0.6
      P(IC=1 | hot)  = 0.2    P(IC=2 | hot)  = 0.4    P(IC=3 | hot)  = 0.4
      P(IC=1 | cold) = 0.5    P(IC=2 | cold) = 0.4    P(IC=3 | cold) = 0.1
      P(hot_0) = 0.8          P(cold_0) = 0.2
    """
    model = ConstrainedMultinomialHMM(
        n_components=2,
        n_features=3,
        random_state=0,
        transmat_mask=None,
    )
    model.startprob_ = np.array([0.8, 0.2])
    model.transmat_ = np.array(
        [
            [0.7, 0.3],   # from hot
            [0.4, 0.6],   # from cold
        ]
    )
    model.emissionprob_ = np.array(
        [
            [0.2, 0.4, 0.4],   # hot
            [0.5, 0.4, 0.1],   # cold
        ]
    )
    return model


def test_v3_3_eisner_ice_cream_signal_in_smoothed_posterior():
    """On Eisner's canonical 3-1-3 sequence, the smoothed posterior at t=2 must
    show a strong COLD signal vs t=1 and t=3.

    Note on Viterbi : with the canonical params from Jurafsky & Martin
    (P_stay=0.7 for hot, P_stay=0.6 for cold), the Viterbi MAP prefers
    HOT-HOT-HOT because likelihood ratio HOT^3 / (HOT-COLD-HOT) ≈ 1.6.
    However the **smoothed marginal** at t=2 strongly suggests COLD
    (~0.45 vs 0.07 at t=1). This is the canonical teaching point :
    smoothing and Viterbi can disagree.

    We test the qualitative signal in smoothed posteriors rather than
    the exact Viterbi output (which depends sensitively on textbook
    edition parameter choices).
    """
    model = _build_eisner_ice_cream()
    X = np.array([[2], [0], [2]])

    posteriors = model.predict_proba(X)
    p_cold = posteriors[:, 1]

    # At t=2 (after seeing only 1 ice cream), the cold signal must rise
    # significantly above its t=1 level
    assert p_cold[1] - p_cold[0] > 0.30, (
        f"Eisner 3-1-3 : COLD signal at t=2 should rise by > 0.30 from t=1. "
        f"Got p_cold = {p_cold} (delta = {p_cold[1] - p_cold[0]:.3f})"
    )
    # At t=3 (after 3 ice creams again), the cold signal must drop back
    assert p_cold[2] < p_cold[1], (
        f"Eisner 3-1-3 : COLD signal at t=3 should drop below t=2 after seeing 3 ice creams. "
        f"Got p_cold = {p_cold}"
    )


def test_v3_3b_eisner_ice_cream_smoothing_two_obs():
    """For Eisner's [3, 1] sequence, the smoothed posterior at t=1 must favor
    HOT (high ice cream consumption) and at t=2 must favor COLD (low).

    We don't pin exact numerical values here because various textbook editions
    use slightly different parameters ; we test the qualitative ordering.
    """
    model = _build_eisner_ice_cream()
    X = np.array([[2], [0]])  # 3 ice creams then 1

    posteriors = model.predict_proba(X)  # (2, 2)

    # t=1 : hot should be > cold
    assert posteriors[0, 0] > posteriors[0, 1], (
        f"After seeing 3 ice creams, hot should dominate ; "
        f"got hot={posteriors[0, 0]:.3f}, cold={posteriors[0, 1]:.3f}"
    )
    # t=2 : cold should be > hot
    assert posteriors[1, 1] > posteriors[1, 0], (
        f"After 3 then 1 ice creams, cold should dominate at t=2 ; "
        f"got hot={posteriors[1, 0]:.3f}, cold={posteriors[1, 1]:.3f}"
    )
