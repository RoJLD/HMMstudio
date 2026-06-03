---
Status: current
---

# Portabilité des modèles sauvegardés — export / import / partage

*Spec écrite le 2026-06-03. Suite de l'Incrément 2 (éditeur de topologie) : le
stop-gap « modèles sauvegardés » (A2) a livré une bibliothèque locale de modèles,
mais ils ne sortent pas du navigateur. Retour utilisateur : « les modèles sont
décrits dans un fichier JSON/txt ? Il faudrait pouvoir les exporter / télécharger
/ partager, et aussi importer un modèle. »*

## 1. Contexte / problème

L'Incrément 2 a ajouté `savedTopologiesStore` : une bibliothèque de modèles nommés
persistée **uniquement en localStorage** (clé `hmm-studio-saved-topologies`), au
format JSON (`Record<name, { name, data: TopologyData, savedAt }>`). Conséquences :

- **Non portables** : perdus si l'utilisateur vide le cache navigateur ; liés à une
  seule machine / un seul navigateur.
- **Non partageables** : aucun moyen d'envoyer un modèle à un collègue.
- **Pas de fichier** : contrairement à l'intuition de l'utilisateur, ce n'est *pas*
  un fichier sur disque.

Or l'éditeur possède **déjà** les briques pour le modèle *courant*
([TopologyPage.tsx]) :
- **Export YAML** — `topologyToYAML(state)` → téléchargement `<name>.yaml`
  (`handleExport`).
- **Import YAML** — fichier `.yaml` → `yamlToTopology` → `loadTopology`
  (`handleImportFile`).
- **Share URL** — `buildShareUrl(state)` → lien base64 → presse-papiers
  (`handleShare`).

Le trou : la **bibliothèque** de modèles sauvegardés n'est branchée à aucune de ces
briques. On ne peut que la *charger* dans l'éditeur.

Le YAML est le **format-modèle canonique** : round-trippable, consommé par le
backend (`/api/fit/start`) et le CLI `hmm-fit`. C'est le « fichier de description »
que l'utilisateur cherche.

## 2. Objectif

Rendre chaque modèle sauvegardé **portable** (exporter en fichier YAML, importer un
fichier dans la bibliothèque, partager par URL) et permettre une **sauvegarde/
restauration de toute la bibliothèque** (JSON), en **réutilisant** les primitives
existantes (`topologyToYAML` / `yamlToTopology` / `buildShareUrl` /
`readSharedTopology`) et sans changement backend. Concevoir le JSON de sauvegarde
**forward-compatible** avec la future docs-map des vrais onglets (A1).

Succès = un chercheur peut : exporter un modèle en `.yaml`, l'envoyer, l'autre
l'importe dans sa bibliothèque ; et sauvegarder/restaurer toute sa bibliothèque
entre deux machines.

## 3. Design

### 3.1 UI — passer le switcher en **liste à actions par ligne**

Le switcher actuel (Incrément 2) est à base de `<select>` (Load / Delete). On ne
peut pas y mettre des actions par modèle. Le remplacer par un petit **panneau/
popover « Mes modèles »** : une ligne par modèle avec **Charger · Exporter · Partager
· Supprimer**, + une barre d'actions bibliothèque (**Importer un modèle**, **Exporter
tout**, **Importer une bibliothèque**). Garde « sauver avant d'écraser » (Inc 2)
conservée sur Charger.

### 3.2 Par modèle sauvegardé

- **Exporter** → télécharge `<name>.yaml` via `topologyToYAML(entry.data)` (réutilise
  exactement le pattern `handleExport`). YAML = échange mono-modèle, lisible par le
  backend/CLI.
- **Partager** → `buildShareUrl(entry.data)` → presse-papiers (réutilise `handleShare`).
  **Limite** : l'URL base64 a une taille max navigateur ; pour un gros modèle, un
  message renvoie vers l'export fichier.

### 3.3 Importer un modèle (fichier → bibliothèque)

- **Importer un modèle** : choisir un `.yaml`/`.yml` → `yamlToTopology` → demander un
  nom (prérempli depuis `topology.name`) → `save()` dans la bibliothèque (au lieu de
  seulement charger dans l'éditeur). Optionnellement « charger aussi dans l'éditeur ».
- **Collision de nom** : si le nom existe déjà → prompt **écraser / renommer**.

### 3.4 Sauvegarde / restauration de toute la bibliothèque

- **Exporter tout** → télécharge `hmm-studio-models.json` :
  ```json
  { "schema_version": 1, "kind": "hmm-studio-model-library", "models": { "<name>": <TopologyData>, ... } }
  ```
  **Forward-compat A1** : `schema_version` + une enveloppe que la future docs-map
  multi-onglets pourra adopter (la `models` map EST la docs-map).
- **Importer une bibliothèque** → choisir un `.json` → valider `kind`/`schema_version`
  → **merge** dans la bibliothèque. Sémantique de collision : par défaut **garder
  l'existant, importer les nouveaux** + option « écraser les existants » (cf.
  Questions ouvertes).

### 3.5 Helpers purs (testables) + réutilisation

- `serializeLibrary(saved): string` et `parseLibrary(text): { models, errors }`
  (`src/lib/modelLibraryIO.ts`) — round-trip JSON + validation `kind`/`schema_version`
  + résolution de collision (fonction pure injectable).
- Réutilise sans dupliquer : `topologyToYAML`, `yamlToTopology` (`lib/yaml.ts`),
  `buildShareUrl`/`readSharedTopology` (`lib/share.ts`), `savedTopologiesStore`.

## 4. Bornes de scope

- **Pas** les vrais onglets A1 (élément roadmap distinct) — mais le JOSN de
  sauvegarde est dessiné pour devenir leur docs-map.
- **Aucun changement backend** : tout client-side ; le YAML est déjà consommable par
  le backend pour le fit/CLI.
- **Pas** de stockage cloud / compte / serveur — fichiers locaux + localStorage.
- Limite de taille du Share-URL **assumée** (gros modèle → fichier).
- Pas de versioning/diff des modèles (ce n'est pas un VCS).

## 5. Questions ouvertes

1. **Merge de bibliothèque** : « garder l'existant + importer les nouveaux » par
   défaut (recommandé) avec option « écraser », ou prompt par nom en collision ?
2. **UI** : popover « Mes modèles » (recommandé) vs garder les `<select>` + ajouter
   un panneau séparé. *À trancher au plan.*
3. **YAML vs JSON pour un modèle seul** : on exporte un modèle en **YAML** (interop
   backend). Faut-il *aussi* un export JSON mono-modèle ? Recommandation : non (YAML
   suffit ; JSON réservé à la bibliothèque).
4. **« Importer un modèle »** doit-il charger dans l'éditeur en plus de la
   bibliothèque, ou seulement sauvegarder ? Recommandation : sauvegarder + proposer
   « charger maintenant ».

## 6. Séquencement et « done »

1. **Helpers purs** `serializeLibrary`/`parseLibrary` + collision (vitest). *Done :*
   round-trip identité, validation `kind`/`schema_version`, collision keep/overwrite.
2. **UI panneau « Mes modèles »** (liste à actions) remplaçant les `<select>`.
3. **Par-modèle export YAML + share** (réutilise handleExport/handleShare).
4. **Import modèle → bibliothèque** (yamlToTopology → save, collision).
5. **Export/Import bibliothèque** (JSON, merge).
6. **E2E** : save → export YAML télécharge ; import YAML → apparaît ; export-all →
   JSON ; import-all → merge. Tests dans le tier existant (vitest + Playwright).

## 7. Pointeurs

- Briques existantes : `pages/TopologyPage.tsx` (handleExport/Import/Share),
  `lib/yaml.ts` (topologyToYAML/yamlToTopology), `lib/share.ts` (buildShareUrl).
- Store : `store/savedTopologiesStore.ts` (Inc 2).
- Lien A1 : la `models` map = la future docs-map multi-onglets (cf. spec
  `2026-06-02-topology-editor-ux-overhaul-design.md`, section A1 roadmap).
