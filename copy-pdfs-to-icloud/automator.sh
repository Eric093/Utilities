/bin/bash -lc '
# Chemins explicites + PATH complet
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Log pour débogage 
LOG="$HOME/Documents/Scripts/copy_pdfs_to_icloud.log"
echo "----- $(date) : démarrage Quick Action" >> "$LOG" 2>&1

# Optionnel : petite pause si un téléchargement est en cours
sleep 2

# Lancer ton script avec chemins sûrs
chmod +x "$HOME/Documents/Scripts/copy-pdfs-to-icloud.sh" >> "$LOG" 2>&1
# xattr -d com.apple.quarantine "$HOME/Documents/Scripts/copy-pdfs-to-icloud.sh" >> "$LOG" 2>&1 || true

"$HOME/Documents/Scripts/copy-pdfs-to-icloud.sh" >> "$LOG" 2>&1

echo "Fin OK" >> "$LOG" 2>&1
'
