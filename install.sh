#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
BACKUP="$HOME_DIR/Custom-Linux-OS-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP" "$HOME_DIR/.themes/Aladin-OS-Futuristic" \
  "$HOME_DIR/.local/share/cinnamon/desklets/AladinOS@local" \
  "$HOME_DIR/.local/bin" "$HOME_DIR/.local/share/icons/hicolor/scalable/apps" \
  "$HOME_DIR/.local/share/applications" "$HOME_DIR/.local/share/plank/themes/Aladin-OS-Futuristic" \
  "$HOME_DIR/Pictures/Custom-Linux-OS"
backup_copy() {
  local src="$1" dst="$2"
  if [[ -e "$dst" ]]; then mkdir -p "$BACKUP/$(dirname "${dst#"$HOME_DIR/"}")"; cp -a "$dst" "$BACKUP/${dst#"$HOME_DIR/"}"; fi
  mkdir -p "$(dirname "$dst")"
  cp -a "$src" "$dst"
}
# Theme files are copied individually so user-created extra files aren't removed.
while IFS= read -r -d '' src; do rel="${src#"$ROOT/theme/"}"; backup_copy "$src" "$HOME_DIR/.themes/Aladin-OS-Futuristic/$rel"; done < <(find "$ROOT/theme" -type f -print0)
backup_copy "$ROOT/desklet/desklet.js" "$HOME_DIR/.local/share/cinnamon/desklets/AladinOS@local/desklet.js"
backup_copy "$ROOT/desklet/stylesheet.css" "$HOME_DIR/.local/share/cinnamon/desklets/AladinOS@local/stylesheet.css"
backup_copy "$ROOT/desklet/metadata.json" "$HOME_DIR/.local/share/cinnamon/desklets/AladinOS@local/metadata.json"
backup_copy "$ROOT/bin/custom-linux-os-control-center.py" "$HOME_DIR/.local/bin/custom-linux-os-control-center.py"
backup_copy "$ROOT/bin/custom-linux-os-app-drawer.py" "$HOME_DIR/.local/bin/custom-linux-os-app-drawer.py"
chmod +x "$HOME_DIR/.local/bin/custom-linux-os-control-center.py" "$HOME_DIR/.local/bin/custom-linux-os-app-drawer.py"
for pair in "custom-linux-os-control-center:custom-linux-os-control-center.py" "custom-linux-os-app-drawer:custom-linux-os-app-drawer.py"; do
  name="${pair%%:*}"; script="${pair#*:}"
  cat > "$HOME_DIR/.local/bin/$name" <<LAUNCH
#!/usr/bin/env bash
exec python3 "$HOME_DIR/.local/bin/$script" "\$@"
LAUNCH
  chmod +x "$HOME_DIR/.local/bin/$name"
done
backup_copy "$ROOT/icons/custom-linux-os.svg" "$HOME_DIR/.local/share/icons/hicolor/scalable/apps/custom-linux-os.svg"
backup_copy "$ROOT/plank/dock.theme" "$HOME_DIR/.local/share/plank/themes/Aladin-OS-Futuristic/dock.theme"
for src in "$ROOT"/wallpapers/*; do [[ -f "$src" ]] || continue; backup_copy "$src" "$HOME_DIR/Pictures/Custom-Linux-OS/$(basename "$src")"; done
for src in "$ROOT"/applications/*.desktop; do [[ -f "$src" ]] || continue; backup_copy "$src" "$HOME_DIR/.local/share/applications/$(basename "$src")"; done
# Keep personal settings.json and Cinnamon enabled-desklets unchanged.
if command -v gtk-update-icon-cache >/dev/null 2>&1; then gtk-update-icon-cache -f -t "$HOME_DIR/.local/share/icons/hicolor" >/dev/null 2>&1 || true; fi
printf 'Installed Custom Linux OS files. Backups (if any): %s\n' "$BACKUP"
printf 'For local bin launchers, ensure %s/.local/bin is on PATH.\n' "$HOME_DIR"
