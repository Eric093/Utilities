# 🧠 AI Prefix Renamer (CLI)

Un outil Python en ligne de commande pour **renommer automatiquement des fichiers** en fonction d’une **expression régulière (regex)**, avec ajout d’un préfixe (ex: `AI_`).

---

## 🚀 Fonctionnalités

* 🔍 Recherche par **regex** dans les noms de fichiers
* 🏷️ Ajout automatique de préfixe (`AI_`, `ML_`, etc.)
* 📂 Mode **dossier** (avec récursivité) ou **fichier unique**
* 🧪 Mode **simulation (dry-run)** sécurisé
* ⚠️ Gestion des collisions :

  * `skip` (ignorer)
  * `overwrite` (écraser)
  * `number` (auto-incrément `(1)`, `(2)`…)
* 📄 Export d’un **log CSV**
* 🤖 Mode non-interactif (`--yes`) pour automatisation
* 🔤 Options avancées : `--ignore-case`, `--word-only`

---

## 📦 Installation

### Prérequis

* Python **3.10+**
* Aucune dépendance externe

### Clone du projet

```bash
git clone https://github.com/ton-utilisateur/ai-prefix-renamer.git
cd ai-prefix-renamer
```

---

## ▶️ Utilisation

### Commande minimale

```bash
python ai_prefix_renamer_cli.py --pattern RAG --prefix AI_
```

---

### Exemple complet

```bash
python ai_prefix_renamer_cli.py \
  --pattern RAG \
  --prefix AI_ \
  --recursive \
  --dry-run \
  --collision number \
  --log-csv
```

---

## 🧭 Interaction

Le script demande ensuite :

```text
Traiter un Dossier ou un Fichier ? (D/F)
```

Puis :

```text
Chemin du dossier ou du fichier :
```

---

## ⚙️ Options CLI

| Option          | Description                   |
| --------------- | ----------------------------- |
| `--pattern`     | Regex à rechercher            |
| `--prefix`      | Préfixe à ajouter             |
| `--recursive`   | Scan récursif                 |
| `--dry-run`     | Simulation sans modification  |
| `--ignore-case` | Ignore la casse               |
| `--word-only`   | Match mot complet (`\b...\b`) |
| `--collision`   | `skip`, `overwrite`, `number` |
| `--yes`         | Pas de confirmation           |
| `--log-csv`     | Génère un log CSV             |

---

## 🧠 Exemple de transformation

| Avant           | Après              |
| --------------- | ------------------ |
| `doc_RAG.txt`   | `AI_doc_RAG.txt`   |
| `RAG_notes.pdf` | `AI_RAG_notes.pdf` |
| `AI_RAG.txt`    | (inchangé)         |

---

## 📊 Log CSV

Un fichier est généré si `--log-csv` est activé :

```
AI_prefix_rename_log_YYYYMMDD_HHMMSS.csv
```

### Contenu

| Champ     | Description                      |
| --------- | -------------------------------- |
| timestamp | Date/heure                       |
| status    | DRY_RUN / RENAMED / SKIP / ERROR |
| old_path  | Chemin d’origine                 |
| new_path  | Nouveau chemin                   |
| reason    | Raison du renommage              |
| error     | Message d’erreur                 |

---

## 📈 Exemple de sortie

```
[DRY]  doc_RAG.txt -> AI_doc_RAG.txt
[SKIP] Cible existe déjà: AI_test.txt

=== Résumé ===
Fichiers analysés : 120
Correspondances   : 35
Simulés           : 35
Skips (collision) : 3
Erreurs           : 0
```

---

## ⚠️ Bonnes pratiques

* Toujours tester avec `--dry-run`
* Vérifier les collisions avant `overwrite`
* Travailler sur une copie de fichiers sensibles
* Utiliser `--log-csv` pour audit

---

## 🔧 Cas d’usage

* Organisation de fichiers IA (RAG, LLM, GPT…)
* Normalisation de noms de fichiers
* Préfixage automatique de documents
* Nettoyage de dossiers volumineux

---

## 🧩 Roadmap

* [ ] Rollback automatique via CSV
* [ ] Filtre par extension (`.pdf`, `.txt`, etc.)
* [ ] Multi-règles (pipeline de renommage)
* [ ] Interface graphique (GUI Tkinter)
* [ ] Export JSON

---

## 📄 Licence

MIT (ou à adapter)

---

## 🤝 Contribution

Les contributions sont les bienvenues :

* Fork
* Branch
* Pull Request

---

## 💡 Auteur

Projet conçu pour automatiser des workflows de renommage avancés avec regex.

---
