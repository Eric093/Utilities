import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def iter_files_in_folder(folder: Path, recursive: bool):
    """Itère sur les fichiers d'un dossier (récursif ou non)."""
    if recursive:
        yield from (p for p in folder.rglob("*") if p.is_file())
    else:
        yield from (p for p in folder.iterdir() if p.is_file())


def compute_new_name(name: str, rx: re.Pattern, prefix: str) -> str | None:
    """
    Retourne le nouveau nom (avec préfixe) si le fichier doit être modifié, sinon None.
    - Ajoute prefix si la regex matche le nom et que le nom ne commence pas déjà par prefix.
    """
    if name.startswith(prefix):
        return None
    if rx.search(name):
        return prefix + name
    return None


def make_unique_name(folder: Path, desired_name: str) -> str:
    """
    Génère un nom unique dans le dossier en ajoutant " (n)" avant l'extension.
    Exemple : AI_file.txt -> AI_file (1).txt
    """
    base, ext = os.path.splitext(desired_name)
    candidate = desired_name
    n = 1
    while (folder / candidate).exists():
        candidate = f"{base} ({n}){ext}"
        n += 1
    return candidate


def rename_path(path: Path, new_name: str, dry_run: bool, collision: str) -> tuple[str, str]:
    """
    Renomme un fichier vers new_name dans le même dossier.
    Retourne (status, message).
    status ∈ {"DRY_RUN","RENAMED","SKIP","ERROR"}

    collision:
      - skip      : ignore si la cible existe
      - overwrite : remplace la cible existante
      - number    : rend le nom unique (AI_x (1).ext)
    """
    target = path.with_name(new_name)

    # Collision
    if target.exists():
        if collision == "skip":
            return "SKIP", f"[SKIP] Cible existe déjà: {target}"
        if collision == "overwrite":
            # On garde le même nom cible; on remplacera avec os.replace
            pass
        if collision == "number":
            unique_name = make_unique_name(path.parent, new_name)
            target = path.with_name(unique_name)
            new_name = unique_name

    if dry_run:
        # En dry-run, on affiche le target final (y compris si "number" a modifié le nom)
        return "DRY_RUN", f"[DRY]  {path.name} -> {new_name}"

    try:
        if collision == "overwrite":
            # os.replace remplace si existe (comportement “overwrite”)
            os.replace(str(path), str(target))
        else:
            path.rename(target)
        return "RENAMED", f"[OK]   {path.name} -> {new_name}"
    except Exception as e:
        return "ERROR", f"[ERR]  {path} : {e}"


def ask_choice() -> str:
    """Demande D ou F en boucle."""
    while True:
        choice = input("Traiter un Dossier ou un Fichier ? (D/F) : ").strip().upper()
        if choice in ("D", "F"):
            return choice
        print("Choix invalide. Réponds par D ou F.")


def ask_path(kind: str) -> Path:
    """Demande le chemin d'un dossier ou d'un fichier."""
    prompt = "Chemin du dossier à traiter : " if kind == "D" else "Chemin du fichier à traiter : "
    while True:
        p = Path(input(prompt).strip().strip('"'))
        if kind == "D" and p.is_dir():
            return p
        if kind == "F" and p.is_file():
            return p
        print("Chemin invalide (introuvable ou mauvais type). Réessaie.")


def ask_yes_no(prompt: str) -> bool:
    """Demande oui/non."""
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("o", "oui", "y", "yes"):
            return True
        if ans in ("n", "non", "no"):
            return False
        print("Réponds par oui/non (o/n).")


def write_csv_log(log_path: Path, rows: list[dict]):
    """Écrit un log CSV (UTF-8)."""
    fieldnames = ["timestamp", "status", "old_path", "new_path", "reason", "error"]
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    parser = argparse.ArgumentParser(
        description="Ajoute un préfixe au nom des fichiers si une regex est trouvée dans le nom."
    )
    parser.add_argument("--pattern", default="RAG", help="Regex à rechercher dans le nom (défaut: RAG)")
    parser.add_argument("--prefix", default="AI_", help="Préfixe à ajouter (défaut: AI_)")
    parser.add_argument("--recursive", action="store_true", help="Scan récursif (dossiers)")
    parser.add_argument("--dry-run", action="store_true", help="Simulation : n'applique pas le renommage")
    parser.add_argument("--ignore-case", action="store_true", help="Ignore la casse (RAG = rag, RaG...)")
    parser.add_argument("--word-only", action="store_true", help="Mot isolé (entoure la regex par \\b...\\b)")

    # ✅ 3 options demandées
    parser.add_argument(
        "--collision",
        choices=["skip", "overwrite", "number"],
        default="skip",
        help="Gestion collision si la cible existe déjà (défaut: skip)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Ne demande pas de confirmation (utile en scripts/automatisation).",
    )
    parser.add_argument(
        "--log-csv",
        action="store_true",
        help="Génère un log CSV des opérations (dans le dossier cible).",
    )

    args = parser.parse_args()

    # Compile regex
    try:
        flags = re.UNICODE | (re.IGNORECASE if args.ignore_case else 0)
        pattern = args.pattern
        if args.word_only and pattern:
            pattern = r"\b" + pattern + r"\b"
        rx = re.compile(pattern, flags)
    except re.error as e:
        print(f"Regex invalide: {e}")
        sys.exit(2)

    print("=== AI Prefix Renamer (CLI) ===")
    print(f"Regex      : {args.pattern}")
    print(f"Préfixe    : {args.prefix}")
    print(f"Récursif   : {args.recursive}")
    print(f"Dry-run    : {args.dry_run}")
    print(f"Collision  : {args.collision}")
    print(f"IgnoreCase : {args.ignore_case}")
    print(f"WordOnly   : {args.word_only}")
    print(f"Log CSV    : {args.log_csv}")
    print()

    kind = ask_choice()
    target_path = ask_path(kind)

    # Confirmation (sauf --yes ou dry-run)
    if not args.yes and not args.dry_run:
        if kind == "F":
            confirm_msg = f"Confirmer le renommage du fichier ?\n{target_path}\n(o/n) : "
        else:
            confirm_msg = f"Confirmer le renommage dans le dossier ?\n{target_path}\n(o/n) : "
        if not ask_yes_no(confirm_msg):
            print("Annulé.")
            sys.exit(0)

    # Prépare log CSV si demandé
    log_rows: list[dict] = []
    log_path: Path | None = None
    if args.log_csv:
        base_dir = target_path if kind == "D" else target_path.parent
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = base_dir / f"AI_prefix_rename_log_{ts}.csv"

    total = 0
    matched = 0
    renamed = 0
    dry = 0
    skipped = 0
    errors = 0

    def process_file(p: Path):
        nonlocal total, matched, renamed, dry, skipped, errors

        total += 1
        new_name = compute_new_name(p.name, rx, args.prefix)
        if new_name is None:
            return

        matched += 1

        status, msg = rename_path(p, new_name, args.dry_run, args.collision)
        print(msg)

        # Comptage
        if status == "RENAMED":
            renamed += 1
        elif status == "DRY_RUN":
            dry += 1
        elif status == "SKIP":
            skipped += 1
        elif status == "ERROR":
            errors += 1

        # Log
        if log_path is not None:
            # new_path réel (attention: en collision number, new_name a été ajusté dans rename_path seulement)
            # Ici, on reconstruit le new_path "attendu" au mieux :
            # - Pour DRY_RUN / RENAMED / SKIP: on peut déduire la cible. Pour number en dry-run, rename_path a ajusté le nom.
            # On encode le new_path selon le message (plus fiable) serait overkill ; on reconstruit simplement:
            #   - Si rename succeeded or dry: on utilise p.with_name(...) MAIS si number modifie, on ne l’a pas ici.
            # Donc on stocke au minimum old_path + new_name initial; la ligne est tout de même utile.
            new_path = str(p.with_name(new_name))
            err = "" if status != "ERROR" else msg

            log_rows.append({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "status": status,
                "old_path": str(p),
                "new_path": new_path,
                "reason": "match",
                "error": err,
            })

    if kind == "F":
        process_file(target_path)
    else:
        for p in iter_files_in_folder(target_path, args.recursive):
            process_file(p)

    if log_path is not None:
        try:
            write_csv_log(log_path, log_rows)
            print(f"\nLog CSV écrit : {log_path}")
        except Exception as e:
            print(f"\nImpossible d'écrire le log CSV : {e}")

    print("\n=== Résumé ===")
    print(f"Fichiers analysés : {total}")
    print(f"Correspondances   : {matched}")
    if args.dry_run:
        print(f"Simulés           : {dry}")
    else:
        print(f"Renommés          : {renamed}")
    print(f"Skips (collision) : {skipped}")
    print(f"Erreurs           : {errors}")


if __name__ == "__main__":
    main()