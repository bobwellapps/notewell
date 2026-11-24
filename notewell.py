#!/usr/bin/env python3
# Notewell - a very basic text editor in a familiar layout.
#
# Copyright (C) 2026 bobwellapps
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version. See the LICENSE file for details.

import getpass
import html
import os
import pwd
import sys

try:
    from PyQt6.QtCore import QDateTime, QLocale, QSettings, QSize, Qt
    from PyQt6.QtGui import (QAction, QFont, QFontDatabase, QIcon, QKeySequence,
                             QTextCursor, QTextDocument, QTextOption)
    from PyQt6.QtPrintSupport import QPageSetupDialog, QPrintDialog, QPrinter
    from PyQt6.QtWidgets import (QApplication, QCheckBox, QDialog, QFileDialog,
                                 QFontDialog, QGridLayout, QGroupBox, QHBoxLayout,
                                 QInputDialog, QLabel, QLineEdit, QMainWindow,
                                 QMessageBox, QPlainTextEdit, QPushButton,
                                 QRadioButton, QVBoxLayout)
except ImportError:
    sys.exit("PyQt6 is missing: sudo apt install python3-pyqt6")

APP_NAME = "Notewell"
VERSION = "1.2"
FILE_FILTER = "Text Documents (*.txt);;All Files (*)"


def decode(data):
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def dropped_file(mime):
    """The path of a single local file being dragged in, or None for anything else."""
    urls = mime.urls()
    if len(urls) == 1 and urls[0].isLocalFile():
        return urls[0].toLocalFile()
    return None


def real_home():
    # Inside a snap $HOME points into ~/snap/<name>/, so ask the system instead
    try:
        return pwd.getpwuid(os.getuid()).pw_dir
    except KeyError:
        return os.environ.get("SNAP_REAL_HOME") or os.path.expanduser("~")


def shell_path(path):
    """The path as it would be typed in a terminal, with ~ for the home folder."""
    home = real_home().rstrip("/")
    if path.startswith(home + "/"):
        return '~/"' + path[len(home) + 1:] + '"'
    return f'"{path}"'


def copy_command(path):
    """The name of a readable copy in the home folder, and the command that makes it."""
    stem, ext = os.path.splitext(os.path.basename(path))
    copy = f"{stem}-copy{ext}"
    return copy, f'sudo cp {shell_path(path)} ~/"{copy}" && sudo chown $USER ~/"{copy}"'


def owner_of(path):
    try:
        return pwd.getpwuid(os.stat(path).st_uid).pw_name
    except (OSError, KeyError):
        return None


RELEASES_URL = "https://github.com/bobwellapps/notewell/releases/latest"
APPIMAGE_TIP = ("The AppImage version of Notewell doesn't have these restrictions, so "
                "you can use that instead. You can download it from:\n"
                f"{RELEASES_URL}\n\n")
SNAP_OPEN_LIMITS = ("Notewell is installed as a snap, and snaps aren't allowed to open "
                    "hidden files (in folders whose names start with a dot), system files "
                    "or files on other drives.\n\n" + APPIMAGE_TIP)
SNAP_SAVE_LIMITS = ("Notewell is installed as a snap, and snaps aren't allowed to save "
                    "files in hidden folders (names starting with a dot), system folders "
                    "or on other drives.\n\n" + APPIMAGE_TIP)


def permission_help(path, saving):
    """Explain a "Permission denied" error and what the user can do about it."""
    owner = owner_of(path)
    someone_else = owner is not None and owner != getpass.getuser()
    # In a snap, a file owned by another user (such as root) would be refused by
    # the AppImage too, so only blame the snap when that isn't the reason.
    in_snap = bool(os.environ.get("SNAP_NAME")) and not someone_else
    belongs = f"It belongs to {owner}, and your" if someone_else else "Your"
    if saving:
        if in_snap:
            return (SNAP_SAVE_LIMITS +
                    "If you still want to use the snap, use File \u2192 Save As to "
                    "save it somewhere in your home folder instead.")
        if os.path.exists(path):
            why = f"{belongs} account isn't allowed to change it."
        else:
            why = "Your account isn't allowed to save files in that folder."
        return (f"{why}\n\nUse File \u2192 Save As to save it somewhere you can "
                "write to, such as your home folder.")

    copy, command = copy_command(path)
    steps = (f"make a copy by running this in a terminal, then open {copy} from "
             f"your home folder:\n\n{command}")
    if in_snap:
        return SNAP_OPEN_LIMITS + "If you still want to use the snap, " + steps
    return (f"{belongs} account isn't allowed to read it. System files such as logs "
            f"often need administrator rights.\n\nTo open it, {steps}")


class TextArea(QPlainTextEdit):
    """The editing area. Dragged text moves as usual; a dropped file is opened."""

    def __init__(self, open_file):
        super().__init__()
        self.open_file = open_file

    def dragEnterEvent(self, event):
        if dropped_file(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if dropped_file(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        path = dropped_file(event.mimeData())
        if path:
            event.acceptProposedAction()
            self.open_file(path)
        else:
            super().dropEvent(event)


class FindDialog(QDialog):
    def __init__(self, window, replace):
        super().__init__(window)
        self.editor_window = window
        self.setWindowTitle("Replace" if replace else "Find")
        self.setMinimumWidth(440)

        self.find_edit = QLineEdit()
        self.find_edit.textChanged.connect(self.update_buttons)
        self.match_case = QCheckBox("Match &case")
        self.replace_edit = None
        self.up = None

        find_label = QLabel("Fi&nd what:")
        find_label.setBuddy(self.find_edit)
        grid = QGridLayout()
        grid.addWidget(find_label, 0, 0)
        grid.addWidget(self.find_edit, 0, 1)

        find_btn = QPushButton("&Find Next")
        find_btn.setDefault(True)
        find_btn.clicked.connect(self.find_next)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        self.buttons = [find_btn]

        if replace:
            self.replace_edit = QLineEdit()
            replace_label = QLabel("Re&place with:")
            replace_label.setBuddy(self.replace_edit)
            grid.addWidget(replace_label, 1, 0)
            grid.addWidget(self.replace_edit, 1, 1)
            grid.addWidget(self.match_case, 2, 0, 1, 2)

            replace_btn = QPushButton("&Replace")
            replace_btn.clicked.connect(self.replace_one)
            replace_all_btn = QPushButton("Replace &All")
            replace_all_btn.clicked.connect(self.replace_all)
            self.buttons += [replace_btn, replace_all_btn]
        else:
            self.up = QRadioButton("&Up")
            down = QRadioButton("&Down")
            down.setChecked(True)
            direction = QGroupBox("Direction")
            row = QHBoxLayout(direction)
            row.addWidget(self.up)
            row.addWidget(down)

            options = QHBoxLayout()
            options.addWidget(self.match_case)
            options.addStretch()
            options.addWidget(direction)
            grid.addLayout(options, 1, 0, 1, 2)

        column = QVBoxLayout()
        for b in self.buttons + [cancel_btn]:
            column.addWidget(b)
        column.addStretch()

        layout = QHBoxLayout(self)
        layout.addLayout(grid, 1)
        layout.addLayout(column)
        self.update_buttons()

    def update_buttons(self):
        for b in self.buttons:
            b.setEnabled(bool(self.find_edit.text()))

    def open_with(self, term, match_case):
        self.find_edit.setText(term)
        self.match_case.setChecked(match_case)
        self.show()
        self.raise_()
        self.activateWindow()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def store(self):
        self.editor_window.term = self.find_edit.text()
        self.editor_window.match_case = self.match_case.isChecked()

    def find_next(self):
        self.store()
        self.editor_window.find(backward=self.up.isChecked(), parent=self)

    def replace_one(self):
        self.store()
        self.editor_window.replace_one(self.replace_edit.text(), parent=self)

    def replace_all(self):
        self.store()
        self.editor_window.replace_all(self.replace_edit.text())


class Notewell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = None
        self.crlf = False
        self.term = ""
        self.match_case = False
        self.printer = None
        self.settings = QSettings("notewell", "notewell")

        self.editor = TextArea(self.open_dropped)
        self.editor.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.setCentralWidget(self.editor)
        self.setAcceptDrops(True)  # files dropped on the menu or status bar

        self.find_dialog = FindDialog(self, replace=False)
        self.replace_dialog = FindDialog(self, replace=True)

        self.pos_label = QLabel()
        self.ending_label = QLabel()
        encoding_label = QLabel("UTF-8")
        for label in (self.pos_label, self.ending_label, encoding_label):
            label.setContentsMargins(8, 0, 8, 0)
        self.statusBar().addWidget(self.pos_label, 1)
        self.statusBar().addPermanentWidget(self.ending_label)
        self.statusBar().addPermanentWidget(encoding_label)

        self.build_menus()
        self.load_settings()

        self.editor.cursorPositionChanged.connect(self.update_status)
        self.editor.document().modificationChanged.connect(self.update_title)
        self.update_title()
        self.update_status()

    def add_action(self, menu, text, slot, shortcut=None, checkable=False):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.setCheckable(checkable)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def build_menus(self):
        keys = QKeySequence.StandardKey
        ed = self.editor
        add = self.add_action

        m = self.menuBar().addMenu("&File")
        add(m, "&New", self.new_file, keys.New)
        add(m, "&Open...", self.open_file, keys.Open)
        add(m, "&Save", self.save, keys.Save)
        add(m, "Save &As...", self.save_as, "Ctrl+Shift+S")
        m.addSeparator()
        add(m, "Page Set&up...", self.page_setup)
        add(m, "&Print...", self.print_file, keys.Print)
        m.addSeparator()
        add(m, "E&xit", self.close)

        m = self.menuBar().addMenu("&Edit")
        undo = add(m, "&Undo", ed.undo, keys.Undo)
        m.addSeparator()
        cut = add(m, "Cu&t", ed.cut, keys.Cut)
        copy = add(m, "&Copy", ed.copy, keys.Copy)
        add(m, "&Paste", ed.paste, keys.Paste)
        delete = add(m, "De&lete", self.delete, "Del")
        m.addSeparator()
        add(m, "&Find...", lambda: self.open_find(False), keys.Find)
        add(m, "Find &Next", lambda: self.find(), "F3")
        add(m, "Find Pre&vious", lambda: self.find(backward=True), "Shift+F3")
        add(m, "&Replace...", lambda: self.open_find(True), "Ctrl+H")
        add(m, "&Go To...", self.go_to, "Ctrl+G")
        m.addSeparator()
        add(m, "Select &All", ed.selectAll, keys.SelectAll)
        add(m, "Time/&Date", self.time_date, "F5")

        for action in (undo, cut, copy, delete):
            action.setEnabled(False)
        ed.undoAvailable.connect(undo.setEnabled)
        for action in (cut, copy, delete):
            ed.copyAvailable.connect(action.setEnabled)

        m = self.menuBar().addMenu("F&ormat")
        self.wrap_action = add(m, "&Word Wrap", self.set_wrap, checkable=True)
        add(m, "&Font...", self.choose_font)

        m = self.menuBar().addMenu("&View")
        self.status_action = add(m, "&Status Bar", self.statusBar().setVisible,
                                 checkable=True)

        m = self.menuBar().addMenu("&Help")
        add(m, f"&About {APP_NAME}", self.about)

    def load_settings(self):
        s = self.settings
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        family = s.value("font_family", "")
        if family:
            font = QFont(family)
            try:
                font.setPointSizeF(float(s.value("font_size", 10)))
            except (TypeError, ValueError):
                pass
            font.setBold(s.value("font_bold") == "true")
            font.setItalic(s.value("font_italic") == "true")
        self.editor.setFont(font)

        wrap = s.value("wrap", "false") == "true"
        status = s.value("status", "true") == "true"
        self.wrap_action.setChecked(wrap)
        self.status_action.setChecked(status)
        self.set_wrap(wrap)
        self.statusBar().setVisible(status)

        size = s.value("size")
        self.resize(size if isinstance(size, QSize) else QSize(800, 560))

    def save_settings(self):
        def flag(on):
            return "true" if on else "false"

        s = self.settings
        font = self.editor.font()
        s.setValue("font_family", font.family())
        s.setValue("font_size", str(font.pointSizeF()))
        s.setValue("font_bold", flag(font.bold()))
        s.setValue("font_italic", flag(font.italic()))
        s.setValue("wrap", flag(self.wrap_action.isChecked()))
        s.setValue("status", flag(self.status_action.isChecked()))
        if not self.isMaximized():
            s.setValue("size", self.size())

    def update_title(self):
        name = os.path.basename(self.path) if self.path else "Untitled"
        star = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{star}{name} - {APP_NAME}")

    def update_status(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self.pos_label.setText(f"Ln {line}, Col {col}")
        self.ending_label.setText("Windows (CRLF)" if self.crlf else "Unix (LF)")

    def confirm_discard(self):
        if not self.editor.document().isModified():
            return True
        btn = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self, APP_NAME,
            f"Do you want to save changes to {self.path or 'Untitled'}?",
            btn.Save | btn.Discard | btn.Cancel, btn.Save)
        if answer == btn.Save:
            return self.save()
        return answer == btn.Discard

    def set_text(self, text):
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.update_title()
        self.update_status()

    def new_file(self):
        if self.confirm_discard():
            self.path = None
            self.crlf = False
            self.set_text("")

    def load(self, path):
        path = os.path.abspath(path)
        try:
            with open(path, "rb") as f:
                text = decode(f.read())
        except FileNotFoundError:
            text = ""  # "notewell new.txt" starts a new file with that name
        except OSError as e:
            self.file_error("open", path, e)
            return
        self.crlf = "\r\n" in text
        self.path = path
        self.set_text(text.replace("\r\n", "\n").replace("\0", " "))

    def file_error(self, action, path, error):
        box = QMessageBox(QMessageBox.Icon.Warning, APP_NAME,
                          f"Cannot {action} {path}\n\n{error.strerror}", parent=self)
        if isinstance(error, PermissionError):
            help_text = permission_help(path, saving=(action == "save"))
            # shown as rich text so the download link can be clicked
            rich = html.escape(help_text).replace("\n", "<br>")
            link = html.escape(RELEASES_URL)
            rich = rich.replace(link, f'<a href="{link}">{link}</a>')
            box.setInformativeText(rich)
        # let people select and copy the text (such as the command to run),
        # and click the link
        for label in box.findChildren(QLabel):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            label.setOpenExternalLinks(True)
        info = box.findChild(QLabel, "qt_msgbox_informativelabel")
        if info:
            info.setTextFormat(Qt.TextFormat.RichText)
        box.exec()

    def open_file(self):
        if not self.confirm_discard():
            return
        start = os.path.dirname(self.path) if self.path else ""
        path, _ = QFileDialog.getOpenFileName(self, "Open", start, FILE_FILTER)
        if path:
            self.load(path)

    def save(self):
        if self.path:
            return self.write(self.path)
        return self.save_as()

    def save_as(self):
        path, chosen = QFileDialog.getSaveFileName(
            self, "Save As", self.path or "Untitled.txt", FILE_FILTER)
        if not path:
            return False
        if chosen.startswith("Text") and not os.path.splitext(path)[1]:
            path += ".txt"
            if os.path.exists(path):
                btn = QMessageBox.StandardButton
                answer = QMessageBox.question(
                    self, "Save As",
                    f"{path} already exists.\nDo you want to replace it?",
                    btn.Yes | btn.No, btn.No)
                if answer != btn.Yes:
                    return False
        return self.write(path)

    def write(self, path):
        text = self.editor.toPlainText()
        if self.crlf:
            text = text.replace("\n", "\r\n")
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        except OSError as e:
            self.file_error("save", path, e)
            return False
        self.path = path
        self.editor.document().setModified(False)
        self.update_title()
        return True

    def get_printer(self):
        if self.printer is None:
            self.printer = QPrinter()
        return self.printer

    def page_setup(self):
        QPageSetupDialog(self.get_printer(), self).exec()

    def print_file(self):
        if QPrintDialog(self.get_printer(), self).exec():
            self.editor.print(self.printer)

    def delete(self):
        self.editor.textCursor().removeSelectedText()

    def open_find(self, replace):
        # A selection on one line becomes the search text.
        # Qt marks line breaks in selectedText() with U+2029.
        selected = self.editor.textCursor().selectedText()
        if selected and " " not in selected:
            self.term = selected
        if replace:
            self.find_dialog.hide()
            self.replace_dialog.open_with(self.term, self.match_case)
        else:
            self.replace_dialog.hide()
            self.find_dialog.open_with(self.term, self.match_case)

    def find_flags(self, backward=False):
        flags = QTextDocument.FindFlag(0)
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        if self.match_case:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def find(self, backward=False, parent=None):
        if not self.term:
            self.open_find(False)
        elif not self.editor.find(self.term, self.find_flags(backward)):
            QMessageBox.information(parent or self, APP_NAME, f'Cannot find "{self.term}"')

    def replace_one(self, replacement, parent=None):
        selected = self.editor.textCursor().selectedText()
        if self.match_case:
            matches = selected == self.term
        else:
            matches = selected.lower() == self.term.lower()
        if self.term and matches:
            self.editor.textCursor().insertText(replacement)
        self.find(parent=parent)

    def replace_all(self, replacement):
        if not self.term:
            return
        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()  # one undo step for the lot
        found = doc.find(self.term, 0, self.find_flags())
        while not found.isNull():
            found.insertText(replacement)
            found = doc.find(self.term, found, self.find_flags())
        cursor.endEditBlock()

    def go_to(self):
        doc = self.editor.document()
        current = self.editor.textCursor().blockNumber() + 1
        line, ok = QInputDialog.getInt(self, "Go To Line", "Line number:",
                                       current, 1, doc.blockCount())
        if ok:
            self.editor.setTextCursor(QTextCursor(doc.findBlockByNumber(line - 1)))

    def time_date(self):
        locale = QLocale.system()
        now = QDateTime.currentDateTime()
        short = QLocale.FormatType.ShortFormat
        self.editor.insertPlainText(
            f"{locale.toString(now.time(), short)} {locale.toString(now.date(), short)}")

    def set_wrap(self, on):
        mode = QPlainTextEdit.LineWrapMode
        self.editor.setLineWrapMode(mode.WidgetWidth if on else mode.NoWrap)
        self.editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)

    def choose_font(self):
        font, ok = QFontDialog.getFont(self.editor.font(), self, "Font")
        if ok:
            self.editor.setFont(font)

    def about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<b>{APP_NAME}</b><br>Version {VERSION}<br><br>"
            "A very basic text editor in a familiar layout.")

    def closeEvent(self, event):
        if self.confirm_discard():
            self.save_settings()
            event.accept()
        else:
            event.ignore()

    def open_dropped(self, path):
        if self.confirm_discard():
            self.load(path)

    def dragEnterEvent(self, event):
        if dropped_file(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = dropped_file(event.mimeData())
        if path:
            self.open_dropped(path)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    # Inside a snap the desktop file is installed as <snap>_<app>.desktop
    snap = os.environ.get("SNAP_NAME")
    app.setDesktopFileName(f"{snap}_notewell" if snap else "notewell")

    icon_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notewell.png")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))
    else:
        app.setWindowIcon(QIcon.fromTheme("notewell"))

    window = Notewell()
    window.show()
    if len(sys.argv) > 1:
        window.load(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
