# Custom Linux OS — Futuristic Cinnamon Theme

A dark glass-style desktop customization for Linux Mint Cinnamon, with an OLED/ice-blue visual identity, custom dashboard desklet, app drawer, Control Center, wallpapers, app icon, and Plank dock styling.

## What's included

- `theme/` — GTK 2/3/4, Cinnamon, libadwaita, and window-manager theme assets.
- `desklet/` — Custom Linux OS Cinnamon dashboard desklet and metadata.
- `bin/` — Python/Tkinter Control Center and searchable application drawer.
- `wallpapers/` — SVG wallpapers.
- `icons/` — App icon.
- `plank/` — Matching Plank dock theme.
- `applications/` — Desktop launcher entries.
- `screenshots/` — Project previews.

## Install

Designed for a user session on Linux Mint Cinnamon. Back up your current theme/desklet files before installing. Run:

```bash
chmod +x install.sh
./install.sh
```

The installer copies only project files into your home directory, creates backups of colliding files under `~/Custom-Linux-OS-backups/`, and does not replace your personal settings JSON or toggle/overwrite your existing Cinnamon enabled-desklets list. After installation, open **Custom Linux OS Control Center** and use **Apply changes** to configure the dashboard.

Dependencies: Python 3, Tkinter, Cinnamon, GTK theme support, and Plank (optional for the dock theme). Some system metrics depend on available hardware sensors.

## Notes and credits

This project is tailored for Cinnamon and includes/adapts theme assets compatible with GTK, Cinnamon, libadwaita, and Xfwm/Openbox. Components originating from Linux Mint or other upstream projects remain subject to their respective licenses and copyrights. Check upstream notices before redistributing modified upstream assets. This repository does not include personal preferences, local AI model files, tokens, credentials, or desktop backup snapshots.

## Current status

A personal desktop customization project; tested on the author's Linux Mint Cinnamon setup. Hardware-specific and desktop-version differences may require adjustment.
