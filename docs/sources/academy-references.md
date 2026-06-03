# Academy references — sourced bibliography

Canonical PDFs, papers and lecture notes that complement the
[Academy lessons](../../src/hmm_studio/frontend/src/lessons/). Each
lesson cites a small subset of this list in its own "Further reading"
section ; the full catalogue lives here.

All URLs are publicly accessible (university course pages, author
self-hosting, open repositories, MIT OpenCourseWare). When multiple
mirrors exist for the same document, the most reliable one (author /
publisher / canonical archive) is listed first.

Tiered by depth and audience :

1. **Tier 1** — Foundational tutorials a practitioner should know.
2. **Tier 2** — Algorithm-specific references for the inference path.
3. **Tier 3** — Variant-specific (NHMM, GMM, Factorial, Hierarchical,
   Bayesian, semi-supervised).
4. **Tier 4** — Domain applications + textbook canonicals.

---

## Tier 1 — Foundational tutorials

### Rabiner 1989 — *A Tutorial on Hidden Markov Models and Selected Applications in Speech Recognition*

Lawrence R. Rabiner. *Proceedings of the IEEE*, vol. 77, no. 2, pp. 257–286.

The single most-cited HMM tutorial. Defines the three canonical
problems (likelihood, decoding, parameter estimation) and walks
through the forward, Viterbi and Baum-Welch algorithms with the
notation that every subsequent textbook still uses.

- [CMU mirror (PDF)](https://www.cs.cmu.edu/~cga/behavior/rabiner1.pdf)
- [Semantic Scholar entry](https://www.semanticscholar.org/paper/A-tutorial-on-hidden-Markov-models-and-selected-in-Rabiner/8fe2ea0a67954f1380b3387e3262f1cdb9f9b3e5)
- [ICDST mirror (PDF)](https://dl.icdst.org/pdfs/files3/4fda5ac4010c90a04f875bd70ccd4242.pdf)

### Bishop PRML — Chapter 13 *Sequential Data*

Christopher M. Bishop. *Pattern Recognition and Machine Learning*,
Springer, 2006.

Treats HMMs inside the broader probabilistic-graphical-model framework
(message passing, conjugate priors, comparison with linear dynamical
systems). Good for readers who already know graphical models.

- [Helsinki TKK chapter PDF](http://www.cis.hut.fi/Opinnot/T-61.6020/2007/sequential_data.pdf)

### Murphy MLAPP — Chapters 17 *Markov and Hidden Markov Models* + 18 *State Space Models*

Kevin P. Murphy. *Machine Learning : A Probabilistic Perspective*,
MIT Press, 2012.

Modern Bayesian framing. Covers HMM filtering / smoothing / Viterbi
plus extensions like switching SSMs.

- [Internet Archive (borrowable)](https://archive.org/details/machinelearningp0000murp)
- [Author TOC PDF](https://www.cs.ubc.ca/~murphyk/MLbook/pml-toc-9apr12.pdf)

### Jurafsky & Martin SLP3 — Appendix A *Hidden Markov Models*

Daniel Jurafsky and James H. Martin. *Speech and Language
Processing*, 3rd edition draft.

NLP-flavored treatment. Walks through the Eisner ice-cream example
and the part-of-speech tagging application end to end.

- [Stanford Appendix A PDF](https://web.stanford.edu/~jurafsky/slp3/A.pdf)

### Russell & Norvig AIMA — Chapter 14-15 *Probabilistic Reasoning Over Time*

The umbrella-world canonical example. Forward and filtering equations
written out as plain probability tables — accessible to anyone who has
done a probability course.

- [Northeastern CSG220 HMM notes (compiled from AIMA)](https://www.khoury.northeastern.edu/home/rjw/csg220/lectures/hmm.pdf)
- [Toronto CS486 Lecture 14 on inference in HMMs](https://www.cs.toronto.edu/~axgao/cs486686_f21/lecture_notes/Lecture_14_on_Hidden_Markov_Models_1.pdf)

---

## Tier 2 — Algorithm-specific references

### Bilmes 1998 — *A Gentle Tutorial of the EM Algorithm and its Application to Parameter Estimation for Gaussian Mixture and Hidden Markov Models*

Jeffrey A. Bilmes. ICSI technical report TR-97-021.

The reference for understanding Baum-Welch as a *concrete instance of
EM*. Derivations are slow and intuitive — perfect companion to Lesson 5.

- [CMU mirror (PDF)](https://www.cs.cmu.edu/~aarti/Class/10701/readings/gentle_tut_HMM.pdf)
- [MRC CBU mirror (PDF)](https://imaging.mrc-cbu.cam.ac.uk/methods/BayesianStuff?action=AttachFile&do=get&target=bilmes-em-algorithm.pdf)

### MIT 6.867 Machine Learning — Lectures 19 & 20 (Hidden Markov Models)

Tommi Jaakkola. Fall 2006. OpenCourseWare.

Slides that derive forward-backward and EM for HMMs from scratch.
Self-contained, no external references needed.

- [Lec 19 (PDF)](https://ocw.mit.edu/courses/6-867-machine-learning-fall-2006/bd962d39492e55697cfa6bb418ae1642_lec19.pdf)
- [Lec 20 — HMM cont'd (PDF)](https://ocw.mit.edu/courses/6-867-machine-learning-fall-2006/1ad9ace4da67d4c396fa56c250dc2b12_lec20.pdf)

### MIT 16.410 Principles of Autonomy and Decision Making — Lecture 21 *Intro to HMM + Baum-Welch*

Emilio Frazzoli. Fall 2010. OpenCourseWare.

Angled at robotics/decision-making rather than NLP. Good if your use
case is sensor sequences or state-machine planning.

- [Lec 21 (PDF)](https://ocw.mit.edu/courses/16-410-principles-of-autonomy-and-decision-making-fall-2010/2ebbc8cc4bc9adc3418a572a17331f63_MIT16_410F10_lec21.pdf)

### Princeton ORF557 — *Hidden Markov Models* lecture notes

Ramon van Handel. Princeton, 2008.

Mathematically rigorous reference notes — measure theory, ergodicity,
asymptotic results. For the student who wants the formal underpinnings.

- [Princeton math PDF](https://web.math.princeton.edu/~rvan/orf557/hmm080728.pdf)

### Concise information-theoretic derivation of Baum-Welch

Iván Hernández et al. arXiv :1406.7002.

Compact alternative derivation of Baum-Welch from a KL-divergence /
maximum-entropy perspective. Useful as a second-pass read after Bilmes.

- [arXiv PDF](https://arxiv.org/pdf/1406.7002)

### Kraskov, Stögbauer & Grassberger 2004 — *Estimating mutual information*

Alexander Kraskov, Harald Stögbauer and Peter Grassberger.
*Physical Review E*, vol. 69, no. 6, 066138.

The k-nearest-neighbour estimator of mutual information for continuous
variables — the estimator that backs
`sklearn.feature_selection.mutual_info_regression` and, through it, the
normalised-MI feature clustering in `hmm_core.features`. Background for
Lesson 13 (unsupervised feature selection).

- [arXiv cond-mat/0305641](https://arxiv.org/abs/cond-mat/0305641)
- [scikit-learn `mutual_info_regression` docs](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_regression.html)

---

## Tier 3 — Variant-specific

### Bengio & Frasconi 1995 — *An Input-Output HMM Architecture* (IOHMM / NHMM)

Yoshua Bengio and Paolo Frasconi. NIPS 1994.

The seminal paper introducing input-conditioned transition and
emission distributions — the direct ancestor of the modern
non-homogeneous HMM (NHMM) implemented in `hmm_core.nhmm`.

- [NeurIPS abstract](https://proceedings.neurips.cc/paper/1994/hash/8065d07da4a77621450aa84fee5656d9-Abstract.html)
- [Bengio 2002 handbook chapter (PDF)](https://bengio.abracadoudou.com/cv/publications/pdf/handbook_2002.pdf)

### Ghahramani & Jordan 1997 — *Factorial Hidden Markov Models*

Zoubin Ghahramani and Michael I. Jordan. *Machine Learning*, 29(2-3).

Distributes the hidden state across D parallel chains, each with its
own dynamics — the model implemented in `hmm_core.factorial_nhmm`.
Discusses exact and variational inference.

- [MIT DSpace AIM-1561 (PDF)](https://dspace.mit.edu/bitstream/handle/1721.1/7188/AIM-1561.pdf?sequence=2)
- [Springer page](https://link.springer.com/article/10.1023/A:1007425814087)

### Fine, Singer & Tishby 1998 — *The Hierarchical Hidden Markov Model*

Shai Fine, Yoram Singer and Naftali Tishby. *Machine Learning*, 32.

Recursive HMM where states can themselves be HMMs — multi-scale
sequences (sub-words → words → phrases). Spec written for our A.11
phase but implementation is gated on external signal.

- [Princeton CS archive PDF](https://www.cs.princeton.edu/courses/archive/spr06/cos598C/papers/FineSingerTishby1998.pdf)
- [Springer PDF](https://link.springer.com/content/pdf/10.1023/A:1007469218079.pdf)

### Reynolds — *Gaussian Mixture Models* tutorial + Columbia E6870 Lec 3 + Edinburgh ASR — *HMMs and GMMs*

Standard GMM-HMM acoustic-model references, all from speech-recognition
course curricula. Background for `hmm_core.gmm_nhmm`.

- [Reynolds GMM tutorial PDF](http://leap.ee.iisc.ac.in/sriram/teaching/MLSP_16/refs/GMM_Tutorial_Reynolds.pdf)
- [Columbia E6870 Lecture 3 (PDF)](https://www.ee.columbia.edu/~stanchen/fall12/e6870/slides/lecture3.pdf)
- [Edinburgh ASR HMM+GMM handout (PDF)](https://www.inf.ed.ac.uk/teaching/courses/asr/2016-17/asr03-hmmgmm-handout.pdf)

### Semi-supervised HMM training

For our `fit(states=NaN)` path (Phase A.7.1).

- [Tamposis et al. 2019 — *Semi-supervised learning of HMMs for biological sequence analysis*](https://academic.oup.com/bioinformatics/article/35/13/2208/5184961)
- [BMC Bioinformatics 2021 — *Partial-label HMM training*](https://ncbi.nlm.nih.gov/pmc/articles/PMC7995745)
- [Springer — *Partially-Hidden Markov Models*](https://link.springer.com/chapter/10.1007/978-3-642-29461-7_42)

### Bayesian HMM (PyMC / Stan)

For our `BayesianHMMBackend` (Phase A.6 / I.3).

- [Damiano et al. — Stan HMM tutorial (PDF)](https://luisdamiano.github.io/stancon18/hmm_stan_tutorial.pdf)
- [arXiv 2509.17806 — Bayesian non-homogeneous HMMs](https://arxiv.org/pdf/2509.17806)

### Lee & McLachlan 2011 — *Finite mixtures of multivariate skew t distributions*

Sharon X. Lee, Geoffrey J. McLachlan. arXiv:1109.4706 (preprint of the
2014 *Statistics and Computing* paper).

EM updates for unrestricted multivariate skew-t mixtures reduce to truncated
multivariate-t moments computable without Monte Carlo. The authors' R
packages `EMMIXuskew` and `EMMIXcskew` implement this directly. The
practical low-risk upgrade from a Student-T emission when the data is
heavy-tailed AND asymmetric.

— **PDF** : <https://arxiv.org/pdf/1109.4706>

### Foroni, Merlo & Petrella 2024 — *Hidden Markov graphical models with state-dependent generalized hyperbolic distributions*

Beatrice Foroni, Luca Merlo, Lea Petrella. arXiv:2412.03668 (Dec 2024).

HMM with state-conditional generalized hyperbolic emissions, fit by
penalized EM with L1 regularization on state-specific precision matrices.
Applied directly to multivariate financial returns. GH nests Student-T,
NIG and VG as special cases, so this is a strict generalization of the
Student-T baseline.

— **PDF** : <https://arxiv.org/pdf/2412.03668>

### Lorek et al. 2022 — *FlowHMM*

Lorek et al. *Advances in Neural Information Processing Systems 35* (NeurIPS 2022).

Normalizing-flow emission for an HMM, trained by a hybrid Baum-Welch (EM)
for the transition parameters and mini-batch SGD for the flow M-step.
Reference implementation : <https://github.com/tooploox/flowhmm>. Published
experiments are on speech (TIMIT) and generic continuous benchmarks; no
peer-reviewed financial held-out evidence at small sample size.

— **PDF** : <https://proceedings.neurips.cc/paper_files/paper/2022/file/39c5871aa13be86ab978cba7069cbcec-Paper-Conference.pdf>

### Rothfuss et al. ICLR 2020 — *Noise regularization for conditional density estimation*

Jonas Rothfuss, Fábio Ferreira, Simon Boehm, Simon Walther, Maxim Ulrich,
Tamim Asfour, Andreas Krause. ICLR 2020 (arXiv:1907.08982).

Documents the severe MLE overfitting failure mode of MDN, KMN, and
Normalizing Flow Networks on small datasets (including financial returns)
and proposes noise regularization as a remedy. Critical reference when
considering neural density estimators as HMM emissions at n ≈ a few thousand.

— **PDF** : <https://openreview.net/pdf?id=rygtPhVtDS>

### Székely, Rizzo & Bakirov 2007 — *Measuring and testing dependence by correlation of distances*

Gábor J. Székely, Maria L. Rizzo, Nail K. Bakirov. *Annals of Statistics* 35(6),
2769–2794.

Introduces distance correlation, a measure that characterises independence
(``dcor(X, Y) = 0`` iff X and Y are independent, not merely uncorrelated) and
works on continuous and categorical data without density estimation. The Python
``dcor`` package implements it for practical use. Underlies the
``criterion="dcor"`` option of ``unsupervised_feature_selection``.

— **PDF** : <https://projecteuclid.org/journals/annals-of-statistics/volume-35/issue-6/Measuring-and-testing-dependence-by-correlation-of-distances/10.1214/009053607000000505.full>

---

## Tier 4 — Domain applications & textbook canonicals

### Durbin, Eddy, Krogh, Mitchison 1998 — *Biological Sequence Analysis*

Cambridge University Press. The bioinformatics canonical reference.
Profile HMMs, the dishonest-casino example we reproduce in
`notebooks/08_textbook_dishonest_casino.ipynb`, the basis of HMMER.

- [Full book PDF (mcb111 mirror)](http://www.mcb111.org/w06/durbin_book.pdf)
- [Cambridge official page](https://www.cambridge.org/core/books/biological-sequence-analysis/921BB7B78B745198829EF96BC7E0F29D)

### Eisner 2002 — *An Interactive Spreadsheet for Teaching the Forward-Backward Algorithm*

Jason Eisner. JHU. Includes the ice-cream HMM scenario used by
Jurafsky and reproduced in our V.3 validation suite.

- [JHU PDF](https://www.cs.jhu.edu/~jason/papers/eisner.tnlp02.pdf)
- [Gawron mirror](https://gawron.sdsu.edu/compling/course_core/lectures/ice_cream_tutorial.pdf)

---

## How each Academy lesson cites these

| Lesson | Primary references |
|---|---|
| 1. *What is an HMM?* | Rabiner §I-II, AIMA Ch.14-15 (Toronto lecture), Bishop §13.1 |
| 2. *Markov chains* | Murphy §17.1, AIMA via Northeastern compile, Bishop §13.1 |
| 3. *Forward algorithm* | Rabiner §III.A, Jurafsky SLP3 §A.2, MIT 6.867 Lec 19 |
| 4. *Viterbi* | Rabiner §III.B, Jurafsky SLP3 §A.4, Bilmes §6 |
| 5. *Baum-Welch* | **Bilmes 1998** (cornerstone), Rabiner §III.C, MIT 16.410 Lec 21, Eisner ice-cream |
| 6. *Constrained topologies* | Rabiner §V (left-right / Bakis), Durbin Ch.5 (profile HMM) |
| 7. *NHMM* | Bengio & Frasconi 1995, Bengio 2002 handbook chapter |
| 13. *Choosing features for your HMM* | Kraskov et al. 2004 (NMI), Székely-Rizzo-Bakirov 2007 (dcor) |
| 14. *Comparing models honestly* | re-benchmark methodology in `Projet_Robin/benchmark/` (no central refs cited) |
| 15. *Choosing the emission distribution* | Lee & McLachlan 2011, Foroni-Merlo-Petrella 2024, FlowHMM NeurIPS 2022, Rothfuss et al. ICLR 2020 |

## Open follow-ups

If the Academy gains advanced lessons in the future, the following
references map :

| Lesson | Reference |
|---|---|
| GMM-HMM regimes | Reynolds + Columbia E6870 Lec 3 + Edinburgh ASR |
| Factorial multi-factor | Ghahramani & Jordan 1997 |
| Bayesian uncertainty | Stan HMM tutorial + arXiv 2509.17806 |
| Semi-supervised | Tamposis 2019 + BMC 2021 + Springer PHMM |
| Hierarchical HMM | Fine, Singer & Tishby 1998 |
| Choosing features | Kraskov et al. 2004 + scikit-learn `mutual_info_regression` |
