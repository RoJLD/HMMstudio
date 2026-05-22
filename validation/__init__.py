"""Scientific validation suite for hmm-studio (Phase V).

Separate from ``tests/`` (which test code correctness). This suite tests
**model correctness** : that our HMM implementations produce the right
*numerical* answers on canonical references where the answer is known
analytically or by published reference.

Run with::

    pytest validation/ -v
"""
