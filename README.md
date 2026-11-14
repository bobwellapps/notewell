# Notewell

A very basic text editor in a familiar layout, written in Python with Qt 6.
It uses your system's Qt, so it picks up the desktop theme (Breeze on KDE).

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/notewell)

<img  width="32%" alt="example1" src="https://github.com/user-attachments/assets/08502981-5a52-4288-ab33-50eed82fc211" />
<img  width="32%" alt="example2" src="https://github.com/user-attachments/assets/9eb9d40a-3dfa-4fe0-bc5f-e32f1662e496" />
<img  width="32%" alt="example3" src="https://github.com/user-attachments/assets/ddc28c00-e199-440d-8310-63617265e97a" />



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
