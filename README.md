# Notewell

A very basic text editor in a familiar layout, written in Python with Qt 6.
It uses your system's Qt, so it picks up the desktop theme (Breeze on KDE).



## Running it

    sudo apt install python3-pyqt6
    ./notewell.py [file]

`./install.sh` adds it to your application menu (installs into `~/.local`).

## What's in it

- File: New, Open, Save, Save As, Page Setup, Print, Exit
- Edit: Undo, Cut, Copy, Paste, Delete, Find, Find Next/Previous, Replace,
  Go To, Select All, Time/Date
- Format: Word Wrap, Font
- View: Status Bar
- Reads UTF-8, UTF-16 and ANSI files and saves as UTF-8, keeping Windows
  (CRLF) line endings if the file had them
- Drag a file onto the window to open it
- Remembers your font, word wrap, status bar and window size

## Licence

Notewell is free software, released under the GNU General Public License,
version 3 or (at your option) any later version. See [LICENSE](LICENSE).

The Notewell name and icon are not covered by the licence. If you release
a modified version, please give it a different name and icon.
