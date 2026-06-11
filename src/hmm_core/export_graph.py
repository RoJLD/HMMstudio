"""Export a fitted HMM as a gitnexus ``model-graph`` JSON contract.

A fitted HMM *is* a state-transition graph, so exporting it is a pure,
zero-tracing serialization. This module mirrors :mod:`hmm_core.io` in style
(NumPy docstrings, ``from __future__ import annotations``, stdlib-``json``
friendly dicts, ``ValueError``/``TypeError`` on bad input) and is purely
additive — it does not touch fit/backends/topology.

Two pure functions on a :class:`~hmm_core.fit.FittedModel` produce
serializable dicts matching the gitnexus contract:

- :func:`export_model_graph` — the static structure (states + transitions
  always; observations + emissions for multinomial emissions only).
- :func:`export_activations` — a dynamic overlay decoded from a sequence
  (per-state occupancy + per-transition frequency).

A thin :func:`save_model_graph` writes the dicts to disk as the gitnexus
source-dir contract (``<out_dir>/model-graph.json`` and, given ``X``,
``model-activations.json``).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

try:
    from hmm_core import __version__ as _HMM_VERSION
except Exception:  # pragma: no cover - defensive, version should always exist
    _HMM_VERSION = None

# Edges with weight at or below this threshold are dropped (forbidden/masked
# transitions, zeroed emission probabilities).
_EPS = 1e-9


def _require_fitted(fitted):
    """Validate that ``fitted`` is a canonical FittedModel and return its backend.

    Parameters
    ----------
    fitted : object
        Expected to be a :class:`~hmm_core.fit.FittedModel` exposing a
        ``.model`` backend with a ``transmat_`` attribute.

    Returns
    -------
    object
        The backend model (``fitted.model``).

    Raises
    ------
    TypeError
        If ``fitted`` has no ``.model`` or that backend has no ``transmat_``
        (e.g. a bare ``object()`` or an NHMM/GMM-NHMM wrapper, which are out
        of scope for v1).
    """
    model = getattr(fitted, "model", None)
    if model is None or not hasattr(model, "transmat_"):
        raise TypeError(
            "export_graph expects a FittedModel with .model.transmat_ "
            "(canonical FittedModel)"
        )
    return model


def export_model_graph(fitted, *, name: str | None = None) -> dict:
    """Export a fitted HMM as the gitnexus ``model-graph`` dict.

    Builds the static graph structure: one node per state and one weighted
    edge per non-zero transition (always). For **multinomial** emissions it
    additionally emits one observation node per symbol and one weighted
    emission edge per non-zero emission probability. For continuous emissions
    (gaussian/gmm/poisson) there are no discrete observation symbols, so
    emissions are omitted — the graph is states + transitions, which is still
    a valid, useful model graph.

    Parameters
    ----------
    fitted : hmm_core.fit.FittedModel
        A fitted model exposing ``.model.transmat_`` (K x K) and ``.topology``
        (with ``state_names``, ``name``, ``emission``). For multinomial
        emissions ``.model.emissionprob_`` (K x n_symbols) is read.
    name : str, optional
        Name recorded under ``model.name``. Defaults to ``fitted.topology.name``.

    Returns
    -------
    dict
        A JSON-serializable dict of the form::

            {
                "model": {"name": ..., "framework": "hmm", "version": ...},
                "nodes": [{"id", "type", "label"}, ...],
                "edges": [{"from", "to", "kind", "weight"}, ...],
            }

        ``type`` is ``"state"`` or ``"observation"``; ``kind`` is
        ``"transition"`` or ``"emission"``.

    Raises
    ------
    TypeError
        If ``fitted`` is not a canonical FittedModel (see :func:`_require_fitted`).
    """
    model = _require_fitted(fitted)
    topo = fitted.topology
    A = np.asarray(model.transmat_)
    names = list(topo.state_names)

    nodes = [{"id": s, "type": "state", "label": s} for s in names]
    edges = []
    for i in range(len(names)):
        for j in range(len(names)):
            w = float(A[i, j])
            if w > _EPS:
                edges.append(
                    {"from": names[i], "to": names[j], "kind": "transition", "weight": w}
                )

    if getattr(topo.emission, "type", None) == "multinomial" and hasattr(
        model, "emissionprob_"
    ):
        B = np.asarray(model.emissionprob_)
        n_sym = B.shape[1]
        for k in range(n_sym):
            nodes.append(
                {"id": f"obs_{k}", "type": "observation", "label": f"obs_{k}"}
            )
        for i in range(len(names)):
            for k in range(n_sym):
                w = float(B[i, k])
                if w > _EPS:
                    edges.append(
                        {
                            "from": names[i],
                            "to": f"obs_{k}",
                            "kind": "emission",
                            "weight": w,
                        }
                    )

    return {
        "model": {
            "name": name or topo.name,
            "framework": "hmm",
            "version": _HMM_VERSION,
        },
        "nodes": nodes,
        "edges": edges,
    }


def export_activations(fitted, X, *, name: str | None = None, lengths=None) -> dict:
    """Export per-state occupancy and per-transition frequency from a sequence.

    Decodes ``X`` and overlays activations onto the model graph:

    - **Node magnitudes** = mean state occupancy, ``predict_proba(X).mean(0)``
      (sums to ~1), keyed by ``state_names``.
    - **Edge frequencies** = counts of consecutive ``(path[t], path[t+1])``
      pairs along the Viterbi path, keyed ``f"{from}->transition->{to}"`` to
      match the gitnexus importer edge-id convention.

    Parameters
    ----------
    fitted : hmm_core.fit.FittedModel
        A fitted model exposing ``.model.predict`` / ``.model.predict_proba``
        and ``.topology`` / ``.seed``.
    X : array-like
        Observation sequence to decode, shape (T, ...).
    name : str, optional
        Name recorded under ``model.name``. Defaults to ``fitted.topology.name``.
    lengths : sequence of int, optional
        hmmlearn multi-sequence lengths. Passed through to ``predict`` /
        ``predict_proba`` when those accept it, and used so transitions are
        NOT counted across sequence boundaries.

    Returns
    -------
    dict
        A JSON-serializable dict of the form::

            {
                "model": {"name": ..., "version": ...},
                "run": {"n_samples": int, "seed": int},
                "nodes": {state_name: occupancy_float, ...},
                "edges": {"from->transition->to": int_count, ...},
            }

        Only observed transitions (count > 0) are emitted.

    Raises
    ------
    TypeError
        If ``fitted`` is not a canonical FittedModel (see :func:`_require_fitted`).
    """
    model = _require_fitted(fitted)
    topo = fitted.topology
    names = list(topo.state_names)
    X = np.asarray(X)

    def _call(method):
        # predict / predict_proba may or may not accept lengths; try then fall back.
        if lengths is not None:
            try:
                return method(X, lengths=lengths)
            except TypeError:
                pass
        return method(X)

    gamma = np.asarray(_call(model.predict_proba))  # (T, K)
    occ = gamma.mean(axis=0)
    node_mag = {names[i]: float(occ[i]) for i in range(len(names))}

    path = np.asarray(_call(model.predict)).astype(int)  # (T,)

    # Transition counts, NOT crossing sequence boundaries given by `lengths`.
    counts: dict[str, int] = {}
    bounds: set[int] = set()
    if lengths is not None:
        c = 0
        for length in lengths:
            c += int(length)
            bounds.add(c - 1)  # last index of each sequence: no transition out
    for t in range(len(path) - 1):
        if t in bounds:
            continue
        i, j = int(path[t]), int(path[t + 1])
        key = f"{names[i]}->transition->{names[j]}"
        counts[key] = counts.get(key, 0) + 1

    return {
        "model": {"name": name or topo.name, "version": _HMM_VERSION},
        "run": {"n_samples": int(len(X)), "seed": int(getattr(fitted, "seed", 0))},
        "nodes": node_mag,
        "edges": counts,
    }


def save_model_graph(fitted, out_dir, *, name: str | None = None, X=None) -> None:
    """Write ``model-graph.json`` (and optionally ``model-activations.json``).

    Thin convenience over :func:`export_model_graph` / :func:`export_activations`
    matching the gitnexus source-dir contract (``<source>/model-graph.json``).

    Parameters
    ----------
    fitted : hmm_core.fit.FittedModel
        The fitted model to export.
    out_dir : str or pathlib.Path
        Directory to write into; created (with parents) if missing.
    name : str, optional
        Name forwarded to the export functions.
    X : array-like, optional
        If given, ``model-activations.json`` is also written by decoding ``X``.

    Returns
    -------
    None

    Raises
    ------
    TypeError
        If ``fitted`` is not a canonical FittedModel (see :func:`_require_fitted`).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "model-graph.json").write_text(
        json.dumps(export_model_graph(fitted, name=name), indent=2),
        encoding="utf-8",
    )
    if X is not None:
        (out / "model-activations.json").write_text(
            json.dumps(export_activations(fitted, X, name=name), indent=2),
            encoding="utf-8",
        )
