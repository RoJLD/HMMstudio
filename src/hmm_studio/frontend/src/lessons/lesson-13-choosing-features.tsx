import { FurtherReading } from "../components/academy/FurtherReading";

export function Lesson13ChoosingFeatures() {
  return (
    <>
      <h2 className="text-xl font-semibold text-slate-900 mb-3">
        Too many candidate indicators
      </h2>
      <p className="text-slate-700 mb-4">
        Every lesson so far assumed you already knew <em>which</em>{" "}
        observations to feed the HMM. In practice you often start with a
        panel of 30-40 candidate columns — on-chain crypto metrics,
        technical indicators, macro series — and no obvious way to pick.
      </p>
      <p className="text-slate-700 mb-4">
        Feeding all of them is a mistake. Many of those columns measure
        the same underlying thing : a 7-day and a 14-day moving average
        move together, realised volatility and ATR are near-duplicates,
        three different "momentum" indicators are basically one signal.
        Handing the HMM all of them :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Inflates the emission dimension</strong> without adding
          information — redundant columns cost parameters (means,
          covariances) but carry no new signal.
        </li>
        <li>
          <strong>Slows EM</strong> and makes the covariance harder to
          estimate (more entries, more chance of an ill-conditioned{" "}
          <code>Σ_k</code>).
        </li>
        <li>
          <strong>Hurts interpretability</strong> — when ten correlated
          columns all load on the same regime, you can't tell which one
          the state actually keys off.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        The idea : cluster by shared information, keep one per cluster
      </h2>
      <p className="text-slate-700 mb-4">
        The cleanest fix is to <strong>group features that carry the same
        information</strong> and keep a single representative from each
        group. The grouping criterion is <strong>normalised mutual
        information</strong> (NMI) : a symmetric, [0, 1]-scaled measure of
        how much knowing one feature tells you about another. Unlike
        Pearson correlation, mutual information also catches{" "}
        <em>non-linear</em> dependence — two columns can be uncorrelated
        yet still redundant.
      </p>
      <p className="text-slate-700 mb-4">
        Two features with NMI near 1 are near-duplicates ; near 0, they
        are roughly independent. Cluster the candidates so that high-NMI
        features land together, then keep one <strong>medoid</strong> per
        cluster — the column most central to its group. The result is a
        strict, decorrelated subset of your original columns.
      </p>
      <p className="text-slate-700 mb-4">
        Crucially this is <strong>unsupervised</strong> : the selector
        never looks at a target or at the HMM's states. It only measures
        redundancy among the candidate features themselves, so there is no
        leakage and nothing to overfit.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        How <code>hmm_core.features</code> does it
      </h2>
      <p className="text-slate-700 mb-4">
        The <code>unsupervised_feature_selection</code> function runs a
        six-step pipeline :
      </p>
      <ol className="list-decimal pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Standardise + jitter</strong> — <code>StandardScaler</code>{" "}
          puts every column on the same scale, then a tiny Gaussian jitter
          (~<code>1e-8</code>) is added because the k-NN mutual-information
          estimator cannot handle exact ties.
        </li>
        <li>
          <strong>Per-feature entropy</strong> <code>H(x_i)</code> via a
          diagonal MI estimate <code>MI(x_i, x_i + jitter)</code> — this is
          the normaliser.
        </li>
        <li>
          <strong>Pairwise NMI</strong>{" "}
          <code>NMI(x_i, x_j) = MI(x_i, x_j) / sqrt(H_i · H_j)</code>,
          clipped to <code>[0, 1]</code>.
        </li>
        <li>
          <strong>Distance</strong> <code>D = 1 - NMI</code> (symmetrised,
          zero diagonal).
        </li>
        <li>
          <strong>Hierarchical clustering</strong> — scipy agglomerative
          linkage (<code>"average"</code> by default ; <code>"ward"</code>{" "}
          is invalid on a 1-NMI distance), dendrogram cut at{" "}
          <code>n_clusters</code>.
        </li>
        <li>
          <strong>Medoid per cluster</strong> — the feature with the
          highest mean NMI to its cluster-mates is retained.
        </li>
      </ol>
      <p className="text-slate-700 mb-4">
        The MI / entropy estimation uses the k-nearest-neighbour estimator
        of Kraskov, Stögbauer &amp; Grassberger (2004) — the same one
        backing <code>sklearn.feature_selection.mutual_info_regression</code>.
        No new dependency : sklearn and scipy were already present.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Using it directly
      </h2>
      <p className="text-slate-700 mb-4">
        Call the function on a clean (NaN-free) DataFrame of candidate
        columns. It returns a rich result : the selected subset plus the
        diagnostics that explain <em>why</em> each column was kept.
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`from hmm_core.features import unsupervised_feature_selection

result = unsupervised_feature_selection(features_df, n_clusters=8)

result.selected            # DataFrame: 8 decorrelated columns, index preserved
result.nmi_matrix          # (p, p) NMI matrix — data for a diagnostic heatmap
result.cluster_dict        # {cluster_id: [feature names in that cluster]}
result.medoid_per_cluster  # {cluster_id: retained feature name}

# Feed the decorrelated subset straight into a fit:
from hmm_core.fit import fit
model = fit(topology, result.selected.values, seed=42)`}</code>
      </pre>
      <p className="text-slate-700 mb-4">
        The <code>nmi_matrix</code> and <code>cluster_dict</code> are worth
        inspecting : the matrix renders as a redundancy heatmap (blocks of
        bright cells = clusters of duplicates), and the cluster dict shows
        exactly which columns were collapsed into each retained medoid.
      </p>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Using it in a prep recipe
      </h2>
      <p className="text-slate-700 mb-4">
        For YAML pipelines there is a thin prep op,{" "}
        <code>select_features_unsupervised</code>, that wraps the function
        and returns only the selected columns (the rich NMI metadata is
        available only via the function call). Because the k-NN estimator
        needs clean input, drop NaNs first :
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`steps:
  - op: dropna           # the NMI estimator needs NaN-free input
  - op: select_features_unsupervised
    n_clusters: 8`}</code>
      </pre>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        When to use it — and when not to
      </h2>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Use it</strong> when you have many candidate features and
          suspect redundancy — a wide on-chain panel, a grab-bag of
          technical indicators, anything where you couldn't hand-pick the
          columns with confidence.
        </li>
        <li>
          <strong>Skip it</strong> when you already have a small, curated
          feature set. If you're modelling a single log-return series (like
          the Giudici preset), there is nothing to decorrelate — clustering
          one or two columns is pointless.
        </li>
        <li>
          It is unsupervised, so it pairs naturally with the prep layer and
          carries no risk of target leakage. If you need{" "}
          <em>target-aware</em> selection (mRMR and friends), that's a
          separate, deliberately out-of-scope problem.
        </li>
      </ul>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Alternative criterion : distance correlation
      </h2>
      <p className="text-slate-700 mb-4">
        NMI is not the only way to measure shared information. The selector also
        accepts <code className="bg-slate-100 px-1 rounded text-sm">criterion=&quot;dcor&quot;</code>,
        which uses <strong>distance correlation</strong> (Székely, Rizzo &amp;
        Bakirov 2007) instead. dcor is :
      </p>
      <ul className="list-disc pl-6 space-y-2 text-slate-700 mb-4">
        <li>
          <strong>Deterministic.</strong> A closed-form functional of pairwise
          distances. No k-NN estimator, no jitter, no{" "}
          <code className="bg-slate-100 px-1 rounded text-sm">random_state</code>{" "}
          to worry about.
        </li>
        <li>
          <strong>Characterises independence.</strong>{" "}
          <code className="bg-slate-100 px-1 rounded text-sm">dcor(X, Y) = 0</code>{" "}
          iff X and Y are independent (not just linearly uncorrelated).
        </li>
      </ul>
      <p className="text-slate-700 mb-4">
        The trade-off : dcor is{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">O(n²)</code> per feature
        pair, against{" "}
        <code className="bg-slate-100 px-1 rounded text-sm">~O(n log n)</code> for the
        k-NN MI estimator. On very large samples NMI is faster ; on small-to-medium
        samples dcor is the safer choice because there is nothing to tune and nothing
        stochastic to seed.
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`# Install the optional extra first :
#   pip install "hmm-studio[dcor]"
result = unsupervised_feature_selection(df, n_clusters=8, criterion="dcor")`}</code>
      </pre>
      <p className="text-slate-700 mb-4">
        The YAML pipeline op exposes the same parameter :
      </p>
      <pre className="bg-slate-100 rounded px-3 py-2 text-sm overflow-x-auto mb-4">
        <code>{`steps:
  - op: dropna
  - op: select_features_unsupervised
    n_clusters: 8
    criterion: dcor`}</code>
      </pre>

      <h2 className="text-xl font-semibold text-slate-900 mb-3 mt-8">
        Where to learn more
      </h2>
      <p className="text-slate-700 mb-4">
        The design rationale — why NMI over distance correlation, why no
        PCA, why unsupervised-only — lives in the spec{" "}
        <code>docs/specs/2026-05-27-unsupervised-feature-selection.md</code>.
        The full algorithm is documented in the docstrings of{" "}
        <code>src/hmm_core/features.py</code>. There is no companion
        notebook for this lesson : the function call above is the whole
        workflow.
      </p>

      <FurtherReading
        references={[
          {
            label: "Kraskov, Stögbauer & Grassberger 2004",
            title:
              "Estimating mutual information (Phys. Rev. E 69, 066138) — the k-NN MI estimator",
            url: "https://arxiv.org/abs/cond-mat/0305641",
            note: "the estimator behind sklearn's mutual_info_regression, used for every NMI here",
          },
          {
            label: "scikit-learn — mutual_info_regression",
            title:
              "API + notes on the k-NN mutual-information estimator used by the selector",
            url: "https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_regression.html",
          },
          {
            label: "Academy bibliography",
            title:
              "Central sourced reference list for all Academy lessons",
            url: "https://github.com/RoJLD/HMMstudio/blob/main/docs/sources/academy-references.md",
          },
        ]}
      />
    </>
  );
}
