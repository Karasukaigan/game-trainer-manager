import os, ctypes
from PyQt6.QtWidgets import QListWidget, QMenu, QMessageBox
from PyQt6.QtGui import QAction
from app.config import *
from app.utils.helpers import *

class CustomListWidget(QListWidget):
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
            open_action = QAction(self.tr("打开"), self)
            delete_action = QAction(self.tr("删除"), self)
            menu.addAction(open_action)
            menu.addAction(delete_action)

            open_action.triggered.connect(lambda: self.openSelectedTrainer(item))
            delete_action.triggered.connect(lambda: self.deleteSelectedTrainer(item))

            menu.exec(event.globalPos())

    def openSelectedTrainer(self, item):
        global trainersPath
        try:
            trainer_name = item.text() + '.exe'
            trainer_path = os.path.join(trainersPath, trainer_name)
            if os.path.exists(trainer_path):
                ctypes.windll.shell32.ShellExecuteW(None, "open", trainer_path, None, None, 1)
                self.main_window.append_output_text(f"<span style='color:LightSkyBlue;'>[open]</span> {trainer_path}")
        except Exception as e:
            self.main_window.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

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
                        self.main_window.append_output_text(f"<span style='color:LightSkyBlue;'>[delete]</span> {trainer_path}")
                    except Exception as e:
                        self.main_window.append_output_text(f"<span style='color:red;'>[error]</span> An error occurred while deleting the file: {str(e)}")
                else:
                    pass
        except Exception as e:
            self.main_window.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")