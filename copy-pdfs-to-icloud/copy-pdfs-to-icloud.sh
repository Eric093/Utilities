#!/bin/bash
# copy_pdfs_to_icloud.sh
# Copie les PDF de ~/Downloads vers iCloud Drive (suffixé par nom machine)
# Ignore les fichiers déjà présents
# Notifications macOS + log détaillé (avec rotation & compression .gz) + résumé console
# Options: --no-notify --no-log --quiet --src <path> --dest <path> [-h|--help]

set -euo pipefail

# ---------- Helpers ----------
# escape_applescript() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

# notify_impl() {
#   local title="$1" subtitle="$2" message="$3"
#   local etitle esub emsg
#   etitle=$(printf "%s" "$title"  | escape_applescript)
#   esub=$(printf "%s" "$subtitle" | escape_applescript)
#   emsg=$(printf "%s" "$message"  | escape_applescript)
#   /usr/bin/osascript -e "display notification \"$emsg\" with title \"$etitle\" subtitle \"$esub\""
# }

# ---------- Helpers ----------
escape_applescript() { sed 's/\\/\\\\/g; s/"/\\"/g'; }

notify_impl() {
  # Respecte --no-notify
  [[ "${ENABLE_NOTIFY:-1}" -eq 1 ]] || return 0

  local title="$1" subtitle="$2" message="$3"

  # 1) Essayer terminal-notifier (chemins communs + PATH)
  for TN in "/opt/homebrew/bin/terminal-notifier" "/usr/local/bin/terminal-notifier" "$(command -v terminal-notifier 2>/dev/null)"; do
    if [[ -n "$TN" && -x "$TN" ]]; then
      # -group permet de regrouper/supplanter les notifs récentes de ce script
      "$TN" -title "$title" -subtitle "$subtitle" -message "$message" -group "copy_pdfs_to_icloud" >/dev/null 2>&1 && return 0
    fi
  done

  # 2) Fallback AppleScript (peut être bloqué par les permissions, mais on essaie)
  local etitle esub emsg
  etitle=$(printf "%s" "$title"  | escape_applescript)
  esub=$(printf "%s" "$subtitle" | escape_applescript)
  emsg=$(printf "%s" "$message"  | escape_applescript)

  if /usr/bin/osascript -e "display notification \"$emsg\" with title \"$etitle\" subtitle \"$esub\"" >/dev/null 2>&1; then
    return 0
  fi
  if /usr/bin/osascript -e "tell application \"System Events\" to display notification \"$emsg\" with title \"$etitle\" subtitle \"$esub\"" >/dev/null 2>&1; then
    return 0
  fi

  # 3) Dernier recours : console
  [[ "${ENABLE_CONSOLE:-1}" -eq 1 ]] && echo "🔔 Notification: $title — $subtitle — $message"
  return 1
}




cecho() { [[ "$ENABLE_CONSOLE" -eq 1 ]] && echo "$@"; }

log_line() {  # usage: log_line LEVEL "message"
  [[ "$ENABLE_LOG" -eq 1 ]] || return 0
  printf "%s [%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$2" >> "$LOG_FILE"
}

rotate_log() {
  [[ "$ENABLE_LOG" -eq 1 ]] || return 0
  local file="$1" max_size="$2" max_backups="$3"
  [[ -f "$file" ]] || return 0
  local size
  size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
  if (( size >= max_size )); then
    local i
    for (( i=max_backups-1; i>=1; i-- )); do
      if [[ -f "${file}.${i}.gz" ]]; then
        mv "${file}.${i}.gz" "${file}.$((i+1)).gz"
      elif [[ -f "${file}.${i}" ]]; then
        /usr/bin/gzip -f "${file}.${i}"
        mv "${file}.${i}.gz" "${file}.$((i+1)).gz"
      fi
    done
    mv "$file" "${file}.1"
    /usr/bin/gzip -f "${file}.1"
    : > "$file"
  fi
}

show_help() {
  cat <<'EOF'
Usage: copy_pdfs_to_icloud.sh [options]

Options:
  --src <path>      Dossier source (défaut: $HOME/Downloads)
  --dest <path>     Dossier destination (défaut: iCloud/PDFs-<Nom_Machine>)
  --no-notify       Désactive la notification macOS
  --no-log          Désactive l'écriture du log (et la rotation)
  --quiet           Aucune sortie console
  -h, --help        Affiche cette aide
EOF
}

# ---------- Defaults & args ----------
MACHINE_NAME=$(/usr/sbin/scutil --get ComputerName | tr ' ' '_')
SRC_DEFAULT="$HOME/Downloads"
DEST_DEFAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/PDFs-$MACHINE_NAME"

SRC="$SRC_DEFAULT"
DEST="$DEST_DEFAULT"

ENABLE_NOTIFY=1
ENABLE_LOG=1
ENABLE_CONSOLE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src) SRC="${2:-}"; shift 2 ;;
    --dest) DEST="${2:-}"; shift 2 ;;
    --no-notify) ENABLE_NOTIFY=0; shift ;;
    --no-log) ENABLE_LOG=0; shift ;;
    --quiet) ENABLE_CONSOLE=0; shift ;;
    -h|--help) show_help; exit 0 ;;
    *) cecho "Option inconnue: $1"; show_help; exit 1 ;;
  esac
done

# ---------- Paths & logging ----------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/copy_pdfs_to_icloud.log"

MAX_LOG_SIZE=$((1024*1024))   # 1 MiB
MAX_LOG_BACKUPS=5

[[ "$ENABLE_LOG" -eq 1 ]] && rotate_log "$LOG_FILE" "$MAX_LOG_SIZE" "$MAX_LOG_BACKUPS"

mkdir -p "$DEST"

# ---------- Error handling ----------
on_error() {
  local ec=$?
  log_line "ERREUR" "Code $ec pendant la copie."
  [[ "$ENABLE_NOTIFY" -eq 1 ]] && notify_impl "Copie des PDFs : Échec" "$MACHINE_NAME" "Une erreur est survenue (code $ec)."
  cecho "❌ Erreur pendant l'opération (code $ec). $( [[ "$ENABLE_LOG" -eq 1 ]] && echo "Voir $LOG_FILE" )"
  exit $ec
}
trap on_error ERR

# ---------- Work ----------
copied=0
skipped=0
declare -a COPIED_FILES
declare -a IGNORED_FILES

sleep 2

# --- Nouvel en-tête daté dans le log ---
if [[ "$ENABLE_LOG" -eq 1 ]]; then
  echo "====================================================" >> "$LOG_FILE"
  echo "📅 Début d'exécution : $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
  echo "Machine=$MACHINE_NAME • SRC=$SRC • DEST=$DEST" >> "$LOG_FILE"
fi

log_line "RUN" "Début du traitement"

while IFS= read -r -d '' file; do
  base="$(basename "$file")"
  target="$DEST/$base"

  if [[ -e "$target" ]]; then
    ((skipped++))
    IGNORED_FILES+=("$base")
    log_line "IGNORE" "$base (déjà présent)"
    continue
  fi

  if /bin/cp -p "$file" "$target"; then
    ((copied++))
    COPIED_FILES+=("$base")
    log_line "COPIE" "$base → $target"
  else
    ((skipped++))
    IGNORED_FILES+=("$base")
    log_line "IGNORE" "$base (échec de copie)"
  fi
done < <(/usr/bin/find "$SRC" -maxdepth 1 -type f \( -iname '*.pdf' \) -print0)

summary="➕ $copied copié(s) • ⏭️ $skipped ignoré(s) • Dest : PDFs-$MACHINE_NAME"

# Notifications
if [[ "$ENABLE_NOTIFY" -eq 1 ]]; then
  if (( copied == 0 )); then
    notify_impl "Copie des PDFs : Rien à faire" "$MACHINE_NAME" "Aucun nouveau PDF à copier."
  else
    notify_impl "Copie des PDFs : Succès" "$MACHINE_NAME" "$summary"
  fi
fi

# Log final — résumé + listes détaillées
if [[ "$ENABLE_LOG" -eq 1 ]]; then
  {
    echo "----- LISTE DES FICHIERS -----"
    echo "--- Copiés ($copied) ---"
    for f in "${COPIED_FILES[@]:-}"; do echo " + $f"; done
    echo "--- Ignorés ($skipped) ---"
    for f in "${IGNORED_FILES[@]:-}"; do echo " - $f"; done
    echo "Résumé: $summary"
    echo
  } >> "$LOG_FILE"
  log_line "OK" "$summary"
fi

# Console
cecho "✅ Opération terminée"
cecho "📂 Dossier destination : $DEST"
cecho "$summary"
if (( copied > 0 )); then
  cecho "Fichiers copiés:"; printf '  + %s\n' "${COPIED_FILES[@]}"
fi
if (( skipped > 0 )); then
  cecho "Fichiers ignorés:"; printf '  - %s\n' "${IGNORED_FILES[@]}"
fi
[[ "$ENABLE_LOG" -eq 1 ]] && cecho "📜 Log: $LOG_FILE (rotation gzip: ${MAX_LOG_BACKUPS} sauvegardes, seuil ${MAX_LOG_SIZE} octets)"
