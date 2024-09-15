from PyQt6.QtWidgets import QListWidget, QMenu
from PyQt6.QtGui import QGuiApplication
from app.config import *
from app.utils.helpers import *

class CustomNameListWidget(QListWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window

    def tr(self, text):
        try:
            return _(text) # type: ignore
        except Exception as e:
            return text

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            menu = QMenu(self)
            copy_zh_name_action = menu.addAction(self.tr("复制中文名"))
            copy_en_name_action = menu.addAction(self.tr("复制英文名"))

            action = menu.exec(self.mapToGlobal(event.pos()))

            if action == copy_zh_name_action:
                self.copy_name_to_clipboard("zh_name", item)
            elif action == copy_en_name_action:
                self.copy_name_to_clipboard("en_name", item)

    def copy_name_to_clipboard(self, name_key, item):
        game_names = item.text().split(' (')
        name_copy = ''
        for game_name in game_names:
            game_name = game_name.replace(")", "")
            if name_key == 'zh_name' and contains_chinese(game_name) and not contains_japanese(game_name):
                name_copy = game_name
            elif name_key == 'en_name' and not contains_chinese(game_name) and not contains_japanese(game_name):
                name_copy = game_name
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(name_copy)

