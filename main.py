import sys, os
from PyQt6.QtWidgets import QApplication
from app.main_window import *
from app.utils.helpers import *
from app.config import *

def main():
    app = QApplication(sys.argv)
    
    if themeStyle == "dark":
        qss_file = 'main_dark.qss'
    else:
        qss_file = 'main_light.qss'

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "stylesheets", qss_file), "r") as file:
        app.setStyleSheet(file.read())

    load_translation()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()