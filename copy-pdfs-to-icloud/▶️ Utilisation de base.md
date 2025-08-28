Parfait ✅ Voici ton **README.md** complet, prêt à être sauvegardé dans le même dossier que ton script.

------

~~~markdown
# 📘 copy_pdfs_to_icloud.sh

## 🎯 Fonction
Copie automatiquement tous les fichiers **PDF** du dossier **Téléchargements** (`~/Downloads`) vers **iCloud Drive**, dans un sous-dossier nommé `PDFs-<Nom_Machine>`.

- Ignore les fichiers déjà présents  
- Conserve les dates & permissions  
- Affiche une **notification visuelle macOS** (via `terminal-notifier`)  
- Produit un **log détaillé** avec rotation (taille max 1 MiB, 5 sauvegardes compressées `.gz`)  
- Affiche un **résumé en console** (option désactivable)  

---

## ⚙️ Dépendances
- macOS ≥ 10.13  
- [terminal-notifier](https://github.com/julienXX/terminal-notifier) (via Homebrew) :  
  ```bash
  brew install terminal-notifier
~~~

------

## ▶️ Utilisation de base

Exécuter simplement :

```bash
~/copy_pdfs_to_icloud.sh
```

- **Source** par défaut : `~/Downloads`

- **Destination** par défaut :

  ```
  ~/Library/Mobile Documents/com~apple~CloudDocs/PDFs-<Nom_Machine>
  ```

------

## 📝 Options disponibles

| Option          | Description                                       |
| --------------- | ------------------------------------------------- |
| `--src <path>`  | Change le dossier source (défaut : `~/Downloads`) |
| `--dest <path>` | Change le dossier destination                     |
| `--no-notify`   | Désactive les notifications macOS                 |
| `--no-log`      | Désactive complètement l’écriture du log          |
| `--quiet`       | Supprime la sortie console                        |
| `-h`, `--help`  | Affiche l’aide rapide                             |

------

## 📂 Exemple d’utilisation

- **Changer le dossier source et destination**

  ```bash
  ~/copy_pdfs_to_icloud.sh --src "$HOME/Téléchargements" --dest "$HOME/Library/Mobile Documents/com~apple~CloudDocs/MesPDFs"
  ```

- **Exécution silencieuse** (pas de console, mais notifications + log)

  ```bash
  ~/copy_pdfs_to_icloud.sh --quiet
  ```

- **Sans notification ni log** (juste console)

  ```bash
  ~/copy_pdfs_to_icloud.sh --no-notify --no-log
  ```

------

## 📜 Gestion des logs

- Log principal : `copy_pdfs_to_icloud.log` (dans le même dossier que le script)
- Rotation automatique :
  - Quand la taille dépasse **1 MiB**, le fichier est archivé en `copy_pdfs_to_icloud.log.1.gz`
  - Les archives existantes sont décalées jusqu’à `.5.gz`

Exemple :

```
copy_pdfs_to_icloud.log
copy_pdfs_to_icloud.log.1.gz
copy_pdfs_to_icloud.log.2.gz
…
```

------

## 🔔 Notifications

- Envoyées via **terminal-notifier** (fiable même depuis Automator)
- Groupées sous l’ID `copy_pdfs_to_icloud` → évite le spam de doublons

Exemple affiché :

```
Copie des PDFs : Succès
MacBook_Eric
➕ 3 copié(s) • ⏭️ 1 ignoré(s)
```

------

```
---

👉 Veux-tu que je génère aussi une **version PDF de ce README** (mise en page simple) pour la garder dans iCloud avec le script et le log ?
```