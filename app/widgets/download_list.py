from PyQt6.QtWidgets import QListWidget, QMenu, QMessageBox
from PyQt6.QtGui import QAction
import webbrowser
from app.config import *
from app.utils.helpers import *

class CustomDownloadListWidget(QListWidget):
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
            download_action = QAction(self.tr("下载"), self)
            open_page_action = QAction(self.tr("打开说明页面"), self)
            menu.addAction(download_action)
            menu.addAction(open_page_action)

            download_action.triggered.connect(lambda: self.downloadTrainer(item))
            open_page_action.triggered.connect(lambda: self.openTrainerPage(item))

            menu.exec(event.globalPos())

    def downloadTrainer(self, item):
        global trainers_data
        try:
            game_name = item.text()
            trainer_data = next((t for t in trainers_data if t['game_name'] == game_name), None)
            if trainer_data:
                download_url = trainer_data['download_url']
                webbrowser.open(download_url)
                self.main_window.append_output_text(f"<span style='color:LightSkyBlue;'>[download]</span> {item.text()} -> {download_url}")
        except Exception as e:
            self.main_window.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def openTrainerPage(self, item):
        global trainers_data
        try:
            game_name = item.text()
            trainer_data = next((t for t in trainers_data if t['game_name'] == game_name), None)
            if trainer_data:
                trainer_url = trainer_data['trainer_url']
                if trainer_url:
                    webbrowser.open(trainer_url)
                    self.main_window.append_output_text(f"<span style='color:LightSkyBlue;'>[open]</span> {item.text()} -> {trainer_url}")
                else:
                    msg_box = QMessageBox(self.main_window)
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText(self.tr("<p>已存档的修改器(2012~2019.05)无说明页面！</p><p>您可以在<a href='https://flingtrainer.com/uncategorized/my-trainers-archive/'>这个页面</a>找到更多信息。</p>"))
                    msg_box.setWindowTitle(self.tr("提示"))
                    ok_button = msg_box.addButton(QMessageBox.StandardButton.Ok)
                    ok_button.setText(self.tr("确定"))
                    msg_box.exec()
        except Exception as e:
            self.main_window.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

                