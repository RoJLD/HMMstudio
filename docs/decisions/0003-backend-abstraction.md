# ADR-0003 : Abstraction `HMMBackend` (isolation du moteur de calcul)

**Date** : 2026-05-22
**Status** : Accepted
**Auteurs** : session parallèle + documentation par la session principale

## Contexte

Sub-projet A (hmm-core v0.1 → v0.2) couplait directement la dispatcher
`fit()` à `hmmlearn` via les sous-classes `Constrained*HMM` dans
`hmm_core.fit.*`. Tout consommateur de hmm-core (CLI, Studio web, scripts
de recherche) héritait de cette dépendance.

L'ADR-0001 acte le choix `hmmlearn` comme backend par défaut, mais ne
verrouille pas l'architecture : la motivation initiale ("on pourra changer
de backend plus tard") n'était que théorique.

Une session parallèle a transformé cette flexibilité théorique en
abstraction réelle, en extrayant un protocole formel et un registre de
backends.

## Décision

Introduire un package `src/hmm_core/backends/` avec :

- **`_protocol.py`** : `HMMBackend` Protocol (runtime-checkable) et
  `BackendFitResult` dataclass. Le protocole décrit cinq méthodes : `fit`,
  `fit_supervised`, `decode`, `predict_proba`, `score`.
- **`_registry.py`** : `register_backend(name, factory, default=False)`,
  `get_backend(name=None)`, `list_backends()`. Registre process-global,
  pattern factory.
- **`hmmlearn_backend.py`** : implémentation concrète `HmmlearnBackend`
  qui délègue aux `Constrained*HMM` (inchangées) et est enregistrée comme
  backend par défaut au moment de l'import du package.

La fonction publique `hmm_core.fit.fit()` accepte maintenant un argument
optionnel `backend: HMMBackend | str | None = None` :

- `None` → backend par défaut (`hmmlearn`).
- `str` → lookup par nom dans le registre.
- instance → utilisée directement.

Le code spécifique à hmmlearn (gestion des `init_params`, paramètres de
constructeur, `_do_mstep`) vit uniquement dans `hmmlearn_backend.py`.

## Alternatives considérées

- **Garder la dispatcher couplée à hmmlearn** (statut pré-refactor). Rejeté :
  toute évolution future (pomegranate, dynamax JAX, NumPy pur, GPU) aurait
  exigé un refactor plus douloureux après accumulation de plus de code.
- **Wrapper hybride sans Protocol formel** (just-a-function backend). Rejeté :
  le contrat aurait été flou; deux backends ne se seraient pas comportés
  pareil sur les corner cases (e.g. `lengths`, `init_params` exclusions).
- **Plugin system avec entry points setuptools**. Reporté : YAGNI tant
  qu'on n'a qu'un seul backend. Le registre interne suffit; on pourra
  basculer sur des entry points si un backend tiers veut se déclarer
  sans patcher le code de hmm-core.

## Conséquences

### Positives

- Découplage net : seul `hmmlearn_backend.py` importe `hmmlearn`. Le reste
  de hmm-core (topology, init, io, cli, nhmm) ne sait pas quel backend est
  utilisé.
- Tests par contrat : `tests/test_backends.py` vérifie le registre et le
  contrat Protocol; les tests de fit deviennent agnostiques.
- Backend tiers possible : un consommateur peut écrire son propre
  `MyBackend(HMMBackend)`, l'enregistrer, et l'utiliser via
  `fit(topo, X, backend=MyBackend())`.
- L'extension "supervised training" (ADR-0004) est venue gratuitement :
  c'est une seconde méthode sur le protocole, pas un patch sur la
  dispatcher.

### Négatives

- Plus de code à parcourir pour qui débute : la dispatcher `fit()` ne
  contient plus la logique de fit, il faut suivre l'indirection via
  `get_backend()`. Mitigé par le docstring qui pointe vers `backends/`.
- Le protocole formel doit évoluer en lockstep si une nouvelle exigence
  apparaît (e.g. fit "streaming" partiel). Documenté dans `_protocol.py`.
- Pas de plugin system extérieur : un backend tiers doit appeler
  `register_backend()` au moment de l'import. Acceptable pour la phase
  actuelle, à revoir si la communauté écrit ses propres backends.

## Tests qui valident cette décision

- `tests/test_backends.py` :
  - `test_default_backend_is_hmmlearn` : le défaut est bien le wrap hmmlearn.
  - `test_get_backend_by_name` / `test_get_backend_unknown_raises` :
    sémantique du registre.
  - Plus des tests de contrat sur les méthodes `fit`/`decode`/etc.
- Tous les tests existants de `tests/test_constraints_*.py`,
  `tests/test_fit_dispatcher.py`, `tests/test_integration_smoke.py`
  continuent de passer sans modification → preuve de la non-régression.

## Revisit triggers

- Un deuxième backend (pomegranate, dynamax) est implémenté → le contrat
  Protocol doit être stress-testé contre cette deuxième implémentation.
  Probable que des arrachements de contrat apparaissent.
- Besoin de fit "streaming" / "stop-and-resume" qui n'est pas exprimable
  dans le contrat actuel.
- Plugin externe (entry points) demandé.

## Pointeurs

- `src/hmm_core/backends/__init__.py`
- `src/hmm_core/backends/_protocol.py`
- `src/hmm_core/backends/_registry.py`
- `src/hmm_core/backends/hmmlearn_backend.py`
- `tests/test_backends.py`
- ADR-0001 (choix hmmlearn comme premier backend) : [0001-backend-hmmlearn-patch.md](0001-backend-hmmlearn-patch.md)
- ADR-0004 (supervised training, qui s'appuie sur ce protocole) : [0004-supervised-training.md](0004-supervised-training.md)
