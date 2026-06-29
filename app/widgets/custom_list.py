import os, ctypes
from PySide6.QtWidgets import QListWidget, QMenu, QMessageBox
from PySide6.QtGui import QAction, QColor, QBrush
from app.config import *
from app.utils.helpers import *

PIN_FILE = 'pin_to_top.csv'

class CustomListWidget(QListWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self._hovered_item = None
        self.setMouseTracking(True)
        self.itemEntered.connect(self._on_item_entered)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def tr(self, text):
        try:
            return _(text)
        except Exception:
            return text

    def _get_pin_file_path(self):
        resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources')
        return os.path.join(resources_path, PIN_FILE)

    def _migrate_old_txt(self):
        resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources')
        old_path = os.path.join(resources_path, 'pin_to_top.txt')
        new_path = self._get_pin_file_path()
        if os.path.exists(old_path) and not os.path.exists(new_path):
            with open(old_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            if lines:
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write('trainer_name\n')
                    f.write('\n'.join(lines))
            os.remove(old_path)

    def _read_pinned(self):
        self._migrate_old_txt()
        path = self._get_pin_file_path()
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        if not lines:
            return []
        return lines[1:]

    def _write_pinned(self, names):
        path = self._get_pin_file_path()
        with open(path, 'w', encoding='utf-8') as f:
            f.write('trainer_name\n')
            f.write('\n'.join(names))

    def _get_default_brush(self):
        if themeStyle == 'dark':
            return QBrush(QColor(30, 30, 30))
        return QBrush(QColor(255, 255, 255))

    def _get_pin_brush(self):
        if themeStyle == 'dark':
            return QBrush(QColor(48, 48, 48))
        return QBrush(QColor(232, 232, 232))

    def _update_pinned_style(self):
        pinned = self._read_pinned()
        default_brush = self._get_default_brush()
        pin_brush = self._get_pin_brush()
        for i in range(self.count()):
            item = self.item(i)
            if item.text() in pinned:
                item.setBackground(pin_brush)
            else:
                item.setBackground(default_brush)

    def _on_item_entered(self, item):
        self._hovered_item = item
        self._update_pinned_style()

    def _on_selection_changed(self):
        self._update_pinned_style()

    def leaveEvent(self, event):
        self._hovered_item = None
        self._update_pinned_style()
        super().leaveEvent(event)

    def clear(self):
        self._hovered_item = None
        super().clear()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            menu = QMenu(self)
            open_action = QAction(self.tr("打开"), self)
            pin_action = QAction(self.tr("置顶"), self)
            delete_action = QAction(self.tr("删除"), self)

            menu.addAction(open_action)
            menu.addAction(pin_action)

            is_pinned = item.text() in self._read_pinned()
            if is_pinned:
                unpin_action = QAction(self.tr("取消置顶"), self)
                unpin_action.triggered.connect(lambda: self.unpinTrainer(item))
                menu.addAction(unpin_action)

            menu.addAction(delete_action)

            open_action.triggered.connect(lambda: self.openSelectedTrainer(item))
            pin_action.triggered.connect(lambda: self.pinTrainerToTop(item))
            delete_action.triggered.connect(lambda: self.deleteSelectedTrainer(item))

            menu.exec(event.globalPos())

    def pinTrainerToTop(self, item):
        try:
            trainer_name = item.text()
            pinned = self._read_pinned()
            if trainer_name in pinned:
                pinned.remove(trainer_name)
            pinned.insert(0, trainer_name)
            self._write_pinned(pinned)

            current_row = self.row(item)
            if current_row != 0:
                taken_item = self.takeItem(current_row)
                self.insertItem(0, taken_item)

            self._update_pinned_style()
            self.main_window.append_log(f"{trainer_name} pinned to top")
        except Exception as e:
            self.main_window.append_log(f"An error occurred while pinning trainer: {str(e)}", "error")

    def unpinTrainer(self, item):
        try:
            trainer_name = item.text()
            pinned = self._read_pinned()
            if trainer_name in pinned:
                pinned.remove(trainer_name)
                self._write_pinned(pinned)

            self._update_pinned_style()
            self.main_window.append_log(f"{trainer_name} unpinned from top")
        except Exception as e:
            self.main_window.append_log(f"An error occurred while unpinning trainer: {str(e)}", "error")

    def openSelectedTrainer(self, item):
        global trainersPath
        try:
            trainer_name = item.text() + '.exe'
            trainer_path = os.path.join(trainersPath, trainer_name)
            if os.path.exists(trainer_path):
                ctypes.windll.shell32.ShellExecuteW(None, "open", trainer_path, None, None, 1)
                self.main_window.append_log(f"{trainer_path}", "open")
        except Exception as e:
            self.main_window.append_log(f"An unexpected error occurred: {str(e)}", "error")

    def deleteSelectedTrainer(self, item):
        global trainersPath
        try:
            trainer_name = item.text() + '.exe'
            trainer_path = os.path.join(trainersPath, trainer_name)

            if os.path.exists(trainer_path):
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(self.tr('删除修改器'))
                msg_box.setText(f"<p>{self.tr('确定要删除')} '{item.text()}'?</p><p><span style='color:red;'>{self.tr('此操作不可逆！')}</span></p>")
                btn_yes = msg_box.addButton(self.tr('确定'), QMessageBox.ButtonRole.AcceptRole)
                btn_no = msg_box.addButton(self.tr('取消'), QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(btn_no)
                msg_box.exec()

                if msg_box.clickedButton() == btn_yes:
                    try:
                        os.remove(trainer_path)
                        self.takeItem(self.row(item))

                        pinned = self._read_pinned()
                        if item.text() in pinned:
                            pinned.remove(item.text())
                            self._write_pinned(pinned)

                        self._update_pinned_style()
                        self.main_window.append_log(f"{trainer_path}", "delete")
                    except Exception as e:
                        self.main_window.append_log(f"An error occurred while deleting the file: {str(e)}", "error")
                else:
                    pass
        except Exception as e:
            self.main_window.append_log(f"An unexpected error occurred: {str(e)}", "error")
