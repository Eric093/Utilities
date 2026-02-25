import argparse
import os
import re
import sys
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


def rename_path(path: Path, new_name: str, dry_run: bool) -> tuple[bool, str]:
    """
    Renomme un fichier vers new_name dans le même dossier.
    Retourne (success, message).
    Collisions : skip si la cible existe déjà.
    """
    target = path.with_name(new_name)

    if target.exists():
        return False, f"[SKIP] Cible existe déjà: {target}"

    if dry_run:
        return True, f"[DRY]  {path.name} -> {new_name}"

    try:
        path.rename(target)
        return True, f"[OK]   {path.name} -> {new_name}"
    except Exception as e:
        return False, f"[ERR]  {path} : {e}"


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


def main():
    parser = argparse.ArgumentParser(
        description="Ajoute un préfixe au nom des fichiers si une regex est trouvée dans le nom."
    )
    parser.add_argument("--pattern", default="RAG", help="Regex à rechercher dans le nom de fichier (défaut: RAG)")
    parser.add_argument("--prefix", default="AI_", help="Préfixe à ajouter (défaut: AI_)")
    parser.add_argument("--recursive", action="store_true", help="Scan récursif (dossiers)")
    parser.add_argument("--dry-run", action="store_true", help="Simulation : n'applique pas le renommage")
    parser.add_argument("--ignore-case", action="store_true", help="Ignore la casse (RAG = rag, RaG...)")
    parser.add_argument("--word-only", action="store_true", help="Mot isolé (entoure la regex par \\b...\\b)")

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
    print(f"Regex     : {args.pattern}")
    print(f"Préfixe   : {args.prefix}")
    print(f"Récursif  : {args.recursive}")
    print(f"Dry-run   : {args.dry_run}")
    print(f"IgnoreCase: {args.ignore_case}")
    print(f"WordOnly  : {args.word_only}")
    print()

    kind = ask_choice()
    target_path = ask_path(kind)

    total = 0
    matched = 0
    renamed_ok = 0
    skipped = 0
    errors = 0

    def process_file(p: Path):
        nonlocal total, matched, renamed_ok, skipped, errors
        total += 1

        new_name = compute_new_name(p.name, rx, args.prefix)
        if new_name is None:
            return

        matched += 1
        ok, msg = rename_path(p, new_name, args.dry_run)
        print(msg)

        if ok:
            # ok=True inclut DRY et OK
            renamed_ok += 1
        else:
            if msg.startswith("[SKIP]"):
                skipped += 1
            else:
                errors += 1

    if kind == "F":
        process_file(target_path)
    else:
        for p in iter_files_in_folder(target_path, args.recursive):
            process_file(p)

    print("\n=== Résumé ===")
    print(f"Fichiers analysés : {total}")
    print(f"Correspondances   : {matched}")
    print(f"{'Simulés' if args.dry_run else 'Renommés'}         : {renamed_ok}")
    print(f"Skips (collision) : {skipped}")
    print(f"Erreurs           : {errors}")


if __name__ == "__main__":
    main()