# Reproducible Linux environment for the rSLDS backend (Phase D spike).
# Rationale: ssm (Linderman) has Cython C-extensions that require a C compiler.
# On the Windows host MSVC Build Tools could not be installed (Enterprise admin
# policy), so the rSLDS backend tests run in this Linux container where gcc is
# available. numpy is pinned <2 for compatibility with ssm's older Cython build.
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git \
 && rm -rf /var/lib/apt/lists/*

# numpy<2 + cython must be present BEFORE building ssm (it builds against them).
RUN pip install --no-cache-dir "numpy<2" cython

# hmm_studio runtime deps (subset needed for the rSLDS backend + tests).
RUN pip install --no-cache-dir scipy pandas scikit-learn hmmlearn pytest pyyaml

# Linderman ssm — pinned to the same commit used by sub-project A's benchmark
# (eb6c8aa). --no-build-isolation so the build uses the numpy/cython installed
# above.
RUN pip install --no-cache-dir --no-build-isolation \
    "git+https://github.com/lindermanlab/ssm.git@eb6c8aa33e5311d3564075807dec340759dd8081"

# The hmm_studio repo is bind-mounted at /work at run time; tests run from /work.
# hmm_core lives in /work/src/hmm_core — set PYTHONPATH so it's importable
# without `pip install -e .` (which would require the source at build time and
# defeat the bind-mount-at-runtime pattern).
ENV PYTHONPATH=/work/src
WORKDIR /work
