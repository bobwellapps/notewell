#!/bin/sh
# Install Notewell into ~/.local for the current user.

set -e
cd "$(dirname "$0")"

if ! python3 -c "import PyQt6.QtWidgets" 2>/dev/null; then
    echo "PyQt6 is missing: sudo apt install python3-pyqt6"
    exit 1
fi

APP=~/.local/share/notewell
ICONS=~/.local/share/icons/hicolor/512x512/apps
mkdir -p "$APP" "$ICONS" ~/.local/bin ~/.local/share/applications

install -m 755 notewell.py "$APP/notewell.py"
install -m 644 notewell.png "$APP/notewell.png"
install -m 644 notewell.png "$ICONS/notewell.png"
ln -sf "$APP/notewell.py" ~/.local/bin/notewell
sed "s|^Exec=notewell|Exec=$APP/notewell.py|" notewell.desktop \
    > ~/.local/share/applications/notewell.desktop
update-desktop-database ~/.local/share/applications 2>/dev/null || true

echo "Done - Notewell should now be in your application menu."
