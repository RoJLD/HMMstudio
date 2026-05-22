# ADR-0010 : Data warehouse scope (local-only, no versioning, sidecar YAML)

**Status** : Accepted
**Date** : 2026-05-22
**Related** : [Phase B.10 spec](../specs/2026-05-22-phase-b10-data-warehouse.md), [ADR-0003 backend abstraction](0003-backend-abstraction.md)

## Contexte

Le tab Data livré en B.5 ne gère qu'un upload one-shot. Pour un chercheur
qui compare plusieurs datasets à travers plusieurs topologies et veut
conserver une trace de provenance entre sessions, c'est de la friction
réelle. La Phase B.10 (livrée 2026-05-22, commits `6366d8e` + `68c5ef0`)
ajoute un explorateur de datasets local adossé à des sidecars YAML.

Le besoin glisse naturellement vers le territoire DVC / MLflow / lakeFS /
Delta Lake. Il faut acter par écrit pourquoi on n'y va pas, sinon chaque
contributeur futur re-pose les mêmes questions et la pression au
scope-creep finit par les emporter. Cet ADR formalise les quatre limites
posées dans la spec B.10 § 9.

## Décision

Le warehouse de la Phase B.10 est :

- **Local-only** : un seul chemin filesystem utilisateur, pas de remote
  storage (S3, GCS, Azure Blob).
- **Stateless côté serveur** : pas de table SQL pour indexer les datasets.
  Le filesystem est la source de vérité; le backend scanne à la volée
  (cache mémoire 5 s, invalidation explicite via `/refresh`).
- **Sidecar YAML** : un fichier `<dataset>.hmm.yaml` optionnel à côté de
  chaque dataset porte la métadonnée éditable (nom, description, rôles de
  colonnes, provenance, notes). Sans sidecar, seules les métadonnées
  auto-détectées (taille, mtime, dtypes) sont exposées.
- **Pas de versioning** : pas d'historique des datasets, pas de git-like,
  pas de DVC intégré.

## Justification

### Local-only

Le wedge de `hmm-studio` est la **modélisation HMM**, pas le data
engineering ni le cloud storage (cf. mémoire `hmm-studio positioning`).
Un remote storage réintroduit auth, erreurs réseau, gestion des
credentials, retries — complexité orthogonale qui n'aide personne à
entraîner des HMMs plus vite. Le local-first est aussi cohérent avec le
reste du studio (SQLite pour les jobs, filesystem pour les artifacts).
Un user avec des datasets en S3 peut faire `aws s3 sync` vers son
warehouse local en amont — on ne réplique pas cette couche de sync.

### Pas de DB / pas de versioning

Trois raisons (cf. spec § 1) :

1. **Concurrence mature** : DVC, lakeFS, Delta Lake, MLflow existent,
   sont bien financés, ont des communautés actives. On n'a aucun edge
   pour les concurrencer sur leur terrain.
2. **Wedge ≠ data engineering** : versionner des datasets est une
   discipline orthogonale à l'entraînement HMM. Les utilisateurs qui en
   ont besoin auront déjà DVC en amont du studio.
3. **Problème de sync filesystem ↔ DB** : si on stocke la métadonnée en
   DB, dès qu'un user déplace un fichier dans l'Explorer Windows, la DB
   diverge — qui gagne ? Filesystem-as-source-of-truth supprime
   complètement le problème : pas de sync à maintenir, pas de
   réconciliation à coder.

### Sidecar YAML

Plutôt qu'une table `datasets` en DB, la métadonnée vit dans un fichier
YAML co-localisé :

- **Co-localisation** : copier `btc_2024.csv` + `btc_2024.csv.hmm.yaml`
  ensemble préserve la provenance. Une métadonnée en DB se perd au move.
- **Diffable** : git, code review, inspection visuelle marchent sur YAML.
- **Optionnel** : un dataset sans sidecar reste utilisable (métadonnées
  auto-détectées comme plancher).
- **Éditable hors studio** : n'importe quel éditeur de texte.
- **Coût** : un fichier en plus par dataset. Acceptable à < 100 datasets.

### Limites anti-scope-creep

La spec § 8 énumère cinq successeurs hors-scope, repris ici avec leur
raison de rejet :

- **B.10.1 Versioning git-like** (init du warehouse) → rejeté, territoire
  DVC.
- **B.10.2 Remote storage** (S3, GCS, Azure Blob) → rejeté sauf pivot
  SaaS explicite.
- **B.10.3 Lineage / DAG cross-fits** → rejeté, territoire DVC / MLflow.
  Le lien fit ↔ dataset au niveau `dataset_id` dans la table de jobs
  suffit.
- **B.10.4 Multi-warehouse / workspaces** → reconsidéré seulement si un
  besoin utilisateur validé apparaît.
- **B.10.5 Indexation full-text / search** → overkill à l'échelle visée
  (< 100 datasets).

**Règle générale** : toute feature qui requiert d'écrire une primitive
de data engineering (orchestrator, scheduler, lineage tracker, immutable
storage) est **rejetée par défaut**. Cf. mémoire `hmm-studio scope
discipline` : on refuse les pivots hors HMM-land.

## Conséquences

**Positives** :
- Friction réduite de "upload → fit → discard" à "select → fit → keep".
- Sidecars diffables en git : la métadonnée voyage avec la data.
- Backend ~200 LOC + 12 tests, zéro nouvelle infra.
- Filesystem comme source de vérité élimine la classe de bugs sync
  DB ↔ disk.

**Négatives / coût accepté** :
- Pas d'historique : un dataset écrasé est perdu (documenté dans l'UI).
- Sidecar opinionated : users avec leur propre convention doivent
  adapter. Schéma gardé léger pour limiter la friction.
- Path traversal à défendre à chaque endpoint `rel_path` (testé via
  `test_path_traversal_blocked`).
- Un fichier sidecar en plus par dataset, visuellement bruyant à l'`ls`.

**Réversibilité** : si un user prouve un besoin de versioning, on peut
ajouter une couche DVC-compatible **par-dessus** le scan/sidecar sans
toucher au core. De même pour le remote storage : un adapter `S3Backend`
exposant la même API peut s'ajouter sans casser le code local. La
décision est ouverte vers l'extension, fermée vers la duplication des
outils existants.

## Alternatives rejetées

| Alternative | Pourquoi rejetée |
|---|---|
| DB-backed dataset registry | Sync filesystem ↔ DB, perd la provenance au déplacement, complique le backup Docker |
| Git LFS / DVC auto-init du warehouse | DVC fait mieux et ce n'est pas notre wedge; on hérite de sa sémantique pour rien |
| Manifest centralisé (un seul `warehouse.yaml` à la racine) | Moins robuste au move de fichiers, plus de conflits git en équipe, perd la co-localisation |
| S3 / GCS direct read | Auth + erreurs réseau + creds — complexité orthogonale à la modélisation HMM |
| Embedding d'un catalog (DataHub, OpenMetadata) | La catégorie "data catalog" est un produit multi-an à elle seule |

## Revisit triggers

- Un user a un workflow réel qui requiert versioning ou remote storage →
  intégrer DVC plutôt que reconstruire.
- Warehouse > 500 datasets et scan perceptible → vrai caching (Redis ou
  scan persisté en DB).
- Pivot multi-user / SaaS → reconsidérer le local-only; warehouse
  per-user avec auth.

## Pointeurs

- `src/hmm_studio/server/warehouse.py`, `server/app.py` (endpoints
  `/api/warehouse/*`), `tests/studio/test_warehouse.py`
- Spec : [docs/specs/2026-05-22-phase-b10-data-warehouse.md](../specs/2026-05-22-phase-b10-data-warehouse.md)
- ADR-0003 (backend abstraction) : même esprit — isoler ce qui change,
  garder le core agnostique.
