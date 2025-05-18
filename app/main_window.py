from PyQt6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QMenuBar, QMenu, QLineEdit, QHBoxLayout, QVBoxLayout, QWidget, QFileDialog, QLabel, QScrollArea
from PyQt6.QtCore import Qt, QProcess, QEventLoop, QThread, pyqtSignal, QThreadPool, QRunnable, QObject
from PyQt6.QtGui import QIcon, QPixmap
from app.config import *
from app.utils.helpers import *
from app.utils.update_data import *
from app.widgets.custom_list import *
from app.widgets.download_list import *
from app.widgets.name_list import *
import csv, shutil, sys
import zipfile, rarfile
from retrying import retry
import requests
from datetime import datetime, timedelta
import app.tools as tools

class UpdateDataSignals(QObject):
    update_signal = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)

class UpdateDataRunnable(QRunnable):
    def __init__(self, need_confirm):
        super().__init__()
        self.signals = UpdateDataSignals()
        self.need_confirm = need_confirm
        
    def run(self):
        try:
            # base_url = 'https://raw.githubusercontent.com/Karasukaigan/game-trainer-manager/main/app/resources/'
            base_urls = [
                'https://raw.githubusercontent.com/Karasukaigan/game-trainer-manager/main/app/resources/',
                'https://raw.gitmirror.com/Karasukaigan/game-trainer-manager/main/app/resources/',
                'https://gh-proxy.com/raw.githubusercontent.com/Karasukaigan/game-trainer-manager/main/app/resources/'
            ]
            resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
            downloads = ["trainers_list.csv", "game_names_merged.csv", "abbreviation.csv"]
            for download in downloads:
                downloaded = False
                for base_url in base_urls:
                    download_url = base_url + download
                    local_filename = os.path.join(resources_path, download)
                    self.signals.update_signal.emit(f"<span style='color:yellow;'>[download]</span> {download_url}")
                    try:
                        response = requests.get(download_url, timeout=6)
                        if response.status_code == 200:
                            with open(local_filename, 'wb') as f:
                                f.write(response.content)
                            self.signals.update_signal.emit(f"<span style='color:yellow;'>[save]</span> Download successful : {local_filename}")
                            downloaded = True
                            break
                        else:
                            raise requests.exceptions.RequestException(f"HTTP {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        self.signals.update_signal.emit(f"<span style='color:red;'>[error]</span> Network request error : {str(e)} on {download_url}")
                if not downloaded:
                    raise Exception(f"Failed to download {download} from all URLs")
            self.signals.update_signal.emit(f"<span style='color:LightGreen;'>[success]</span> Data related to the trainers has been updated!")
            if self.need_confirm:
                self.signals.finished.emit(True, tr("更新成功"), tr("修改器相关数据更新完成。"))
            os.execl(sys.executable, sys.executable, *sys.argv)
        except requests.exceptions.RequestException as e:
            self.signals.update_signal.emit(f"<span style='color:red;'>[error]</span> Network request error : {str(e)}")
            if self.need_confirm:
                self.signals.finished.emit(False, tr("更新失败"), tr("网络错误，请稍后再试。"))
        except Exception as e:
            self.signals.update_signal.emit(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")
            if self.need_confirm:
                self.signals.finished.emit(False, tr("更新失败"), tr("网络错误，请稍后再试。"))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.version_number = version_number
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.ini')
        self.trainersPath = trainersPath
        self.names_data = read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', "game_names_merged.csv"))
        self.trainers_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'trainers_list.csv')
        self.trainers_old_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'trainers_list_old.csv')
        self.abbreviation = self.read_abbreviation_from_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', "abbreviation.csv"))
        self.update_time = updateTime
        self.threadpool = QThreadPool()
        self.trainers_data = []

        self.initUI()
        self.loadTrainers()
        self.auto_update(updateTime)
        self.getTrainersData()

    def auto_update(self, last_update_time):
        last_update_datetime = datetime.strptime(last_update_time, "%Y-%m-%d")
        current_date = datetime.now()
        delta = current_date - last_update_datetime
        if delta > timedelta(days=2):
            self.append_output_text(f"<span style='color:red;'>[info]</span> More than two days have passed since {last_update_time}, an update is needed.")
            try:
                self.updateData(False)
                config.set('settings', 'updatetime', current_date.strftime("%Y-%m-%d"))
                with open(self.config_path, 'w') as configfile:
                    config.write(configfile)
                return current_date.strftime("%Y-%m-%d")
            except Exception as e:
                self.append_output_text(f"<span style='color:red;'>[error]</span> Automatic update failed : {e}")
                return ""
        else:
            return ""
        
    def initUI(self):
        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)
        fileMenu = QMenu(tr("文件"), self)
        importAction = fileMenu.addAction(tr("从本地导入修改器"))
        importZipAction = fileMenu.addAction(tr("从压缩包导入修改器"))
        openDirAction = fileMenu.addAction(tr("打开修改器目录"))
        fileMenu.addSeparator()
        updateAction = fileMenu.addAction(tr("更新修改器列表"))
        openListAction = fileMenu.addAction(tr("打开修改器列表"))
        openOldListAction = fileMenu.addAction(tr("打开旧修改器列表"))
        updateAction.triggered.connect(lambda: self.updateData(True))
        importAction.triggered.connect(self.importFiles)
        openDirAction.triggered.connect(self.openDirectory)
        importZipAction.triggered.connect(self.importZipFiles)
        openListAction.triggered.connect(lambda: self.openCsvFile(self.trainers_data_path))
        openOldListAction.triggered.connect(lambda: self.openCsvFile(self.trainers_old_data_path))
        menuBar.addMenu(fileMenu)

        toolsMenu = QMenu(tr("工具"), self)
        downloadToolAction = QAction(tr("隐藏下载器"), self)
        downloadToolAction.triggered.connect(self.downloadTool)
        toolsMenu.addAction(downloadToolAction)
        toggleTranslationSearchAction = QAction(tr("查找翻译"), self)
        toggleTranslationSearchAction.triggered.connect(self.toggleTranslationSearch)
        toolsMenu.addAction(toggleTranslationSearchAction)
        toolsMenu.addSeparator()
        translationFileNameAction = QAction(tr("翻译修改器文件名"), self)
        translationFileNameAction.triggered.connect(self.translationFileName)
        toolsMenu.addAction(translationFileNameAction)
        openSteamAction = QAction(tr("运行Steam"), self)
        openSteamAction.triggered.connect(tools.find_and_run_steam)
        toolsMenu.addAction(openSteamAction)
        menuBar.addMenu(toolsMenu)

        setMenu = QMenu(tr("设置"), self)
        switchThemeAction = setMenu.addAction(tr("切换主题"))
        switchUIAction = setMenu.addAction("Switch to English")
        switchUIAction.triggered.connect(self.switchUI)
        switchThemeAction.triggered.connect(self.switchTheme)
        menuBar.addMenu(setMenu)

        helpMenu = QMenu(tr("帮助"), self)
        openFLiNGAction = helpMenu.addAction(tr("打开风灵月影官网"))
        openArchiveLinkAction = helpMenu.addAction(tr("打开旧修改器列表(2012~2019.05)"))
        openSteamAction = helpMenu.addAction(tr("打开Steam官网"))
        openCELinkAction = helpMenu.addAction(tr("打开Cheat Engine官网"))
        openWeModAction = helpMenu.addAction(tr("打开WeMod官网"))
        helpMenu.addSeparator()
        openGithubAction = helpMenu.addAction(tr("打开GitHub项目页面"))
        aboutAction = helpMenu.addAction(tr("关于"))
        openFLiNGAction.triggered.connect(lambda: self.openUrl("https://flingtrainer.com/all-trainers/"))
        openArchiveLinkAction.triggered.connect(lambda: self.openUrl("https://archive.flingtrainer.com/"))
        openSteamAction.triggered.connect(lambda: self.openUrl("https://store.steampowered.com/"))
        openCELinkAction.triggered.connect(lambda: self.openUrl("https://www.cheatengine.org/"))
        openWeModAction.triggered.connect(lambda: self.openUrl("https://www.wemod.com/"))
        aboutAction.triggered.connect(self.showAboutDialog)
        openGithubAction.triggered.connect(lambda: self.openUrl("https://github.com/Karasukaigan/game-trainer-manager"))
        menuBar.addMenu(helpMenu)

        self.lineEdit1 = QLineEdit(self)
        self.lineEdit2 = QLineEdit(self)
        self.lineEdit3 = QLineEdit(self)
        self.lineEdit1.setPlaceholderText(tr("在已有修改器里搜索"))
        self.lineEdit2.setPlaceholderText(tr("在风灵月影官网搜索"))
        self.lineEdit3.setPlaceholderText(tr("用关键词查询游戏名(按回车查询)"))
        self.lineEdit1.textChanged.connect(self.onLineEdit1TextChanged)
        self.lineEdit2.textChanged.connect(self.onLineEdit2TextChanged)
        self.lineEdit3.keyPressEvent = self.lineEdit3_keyPressEvent
        
        self.listWidgetLeft = CustomListWidget(self, self)
        self.listWidgetRight = CustomDownloadListWidget(self, self)
        self.listWidgetName = CustomNameListWidget(self, self)
        self.listWidgetLeft.itemDoubleClicked.connect(self.listWidgetLeft.openSelectedTrainer)
        self.listWidgetRight.itemDoubleClicked.connect(self.listWidgetRight.downloadTrainer)

        if config.get('settings', 'downloadToolIsHidden') == 'true':
            self.lineEdit2.hide()
            self.listWidgetRight.hide()
            downloadToolAction.setText(tr("下载器"))
        else:
            downloadToolAction.setText(tr("隐藏下载器"))
        if config.get('settings', 'toggleTranslationSearchIsHidden') == 'true':
            self.lineEdit3.hide()
            self.listWidgetName.hide()
            toggleTranslationSearchAction.setText(tr("查找翻译"))
        else:
            toggleTranslationSearchAction.setText(tr("隐藏查找翻译"))
        if config.get('settings', 'enableEnglishUI') == 'true':
            switchUIAction.setText("切换为中文")
        else:
            switchUIAction.setText("Switch to English")

        textBoxLayout = QHBoxLayout()
        textBoxLayout.addWidget(self.lineEdit1)
        textBoxLayout.addWidget(self.lineEdit2)
        textBoxLayout.addWidget(self.lineEdit3)
        listBoxLayout = QHBoxLayout()
        listBoxLayout.addWidget(self.listWidgetLeft)
        listBoxLayout.addWidget(self.listWidgetRight)
        listBoxLayout.addWidget(self.listWidgetName)

        self.output_text_edit = QPlainTextEdit(self)
        self.output_text_edit.setReadOnly(True)
        cmdLayout = QVBoxLayout()
        cmdLayout.addWidget(self.output_text_edit)
        if config.get('settings', 'debugMode') != 'true':
            self.output_text_edit.hide()

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(textBoxLayout)
        mainLayout.addLayout(listBoxLayout)
        mainLayout.addLayout(cmdLayout)

        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        window_width = 800
        window_height = 500
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        if config.get('settings', 'enableEnglishUI') == 'true':
            self.setWindowTitle(f'Game Trainer Manager {version_number}')
        else:
            self.setWindowTitle(f'游戏修改器管理器 {version_number}')
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'logo.png')))

        self.append_output_text(f"<span style='color:LightGreen;'>[info]</span> The main window has been loaded.")
        
        if isFirstStart == 'true':
            self.showAboutDialog()
            config.set('settings', 'isFirstStart', 'false')
            with open(self.config_path, 'w') as configfile:
                config.write(configfile)
    
    def loadTrainers(self):
        try:
            if not os.path.exists(self.trainersPath):
                os.makedirs(self.trainersPath)

            self.trainers = []
            self.listWidgetLeft.clear()

            for root, _, files in os.walk(self.trainersPath):
                for file in files:
                    if file.endswith(".exe"):
                        full_path = os.path.join(root, file)
                        self.trainers.append(full_path)
                        self.listWidgetLeft.addItem(file.split('.exe')[0])
            self.append_output_text(f"<span style='color:LightGreen;'>[info]</span> The list of trainers has been loaded.")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def getTrainersData(self):
        global trainers_data
        trainers_data = []
        try:
            for csv_file in [self.trainers_data_path, self.trainers_old_data_path]:
                with open(csv_file, mode='r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)
                    for row in reader:
                        if str(csv_file).split('\\')[-1] == 'trainers_list.csv':
                            trainer_dict = {
                                'game_name': row[0],
                                'trainer_name': row[1],
                                'trainer_url': row[2],
                                'download_url': row[3]
                            }
                        else:
                            trainer_dict = {
                                'game_name': row[0] + '(Archive)',
                                'trainer_name': row[1],
                                'trainer_url': '',
                                'download_url': row[2]
                            }
                        trainers_data.append(trainer_dict)
            self.trainers_data = trainers_data
            self.append_output_text(f"<span style='color:LightGreen;'>[info]</span> Data for all trainers has been loaded.")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")
    
    def onLineEdit1TextChanged(self, text):
        self.listWidgetLeft.clear()
        try:
            if text.strip():
                similar_names = sorted(self.trainers, key=lambda x: similarity(text, os.path.basename(x)), reverse=True)

                for trainer_path in similar_names:
                    trainer_name = os.path.basename(trainer_path).split('.exe')[0]
                    sim = similarity(text, trainer_name)
                    if sim > 0.8 or text.lower() in trainer_name.lower():
                        self.listWidgetLeft.addItem(trainer_name)
            else:
                self.loadTrainers()
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    
    def read_abbreviation_from_csv(self, file_path):
        abbreviation = {}
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                abbreviation[row[0]] = row[1]
        return abbreviation

    def onLineEdit2TextChanged(self, text):
        global trainers_data
        self.listWidgetRight.clear()
        try:
            if text.strip():
                search_text = [text.lower().replace(":", "")]
                if search_text[0] in self.abbreviation:
                    search_text[0] = self.abbreviation[search_text[0]].lower().replace(":", "")
                if re.search(r'[\u4e00-\u9fff]', text) and len(text) >= 2:
                    similar_games = sorted(self.names_data, key=lambda x: (
                        similarity(search_text[0].replace("：", ""), x['zh_name'].lower().replace(":", "").replace("：", ""))
                    ), reverse=True)
                    for i in range(15):
                        game = similar_games[i]
                        if any(search_text[0].replace("：", "") in game[key].lower().replace(":", "").replace("：", "") for key in ['zh_name']):
                            search_text.append(game['en_name'].lower().replace(":", ""))
                existing_games = []
                for trainer in self.trainers_data:
                    for this_text in search_text:
                        game_name = trainer['game_name']
                        sim = similarity(this_text, game_name.lower().replace(":", ""))
                        if sim > 0.8 or this_text in game_name.lower():
                            if game_name not in existing_games:
                                existing_games.append(game_name)
                                self.listWidgetRight.addItem(game_name)
            else:
                self.listWidgetRight.clear()
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def lineEdit3_keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.onLineEdit3TextChanged(self.lineEdit3.text())
        else:
            QLineEdit.keyPressEvent(self.lineEdit3, event)

    def onLineEdit3TextChanged(self, text):
        self.listWidgetName.clear()
        
        if not text:
            self.listWidgetName.clear()
            return

        try:
            similar_games = sorted(self.names_data, key=lambda x: (
                similarity(text.lower(), x['en_name'].lower()),
                similarity(text.lower(), x['zh_name'].lower())
            ), reverse=True)
            
            for game in similar_games:
                sim = [similarity(text, game[key]) for key in ['en_name', 'zh_name']]
                if max(sim) > 0.8 or any(text.lower() in game[key].lower() for key in ['en_name', 'zh_name']):
                    game_name = game['zh_name'] or game['en_name']
                    if game['en_name'] and game['en_name'] != game_name:
                        game_name += f" ({game['en_name']})"
                    self.listWidgetName.addItem(game_name)
            self.append_output_text(f"<span style='color:LightGreen;'>[success]</span> Query results have been obtained.")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def updateData(self, need_confirm):
        if need_confirm:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(tr('更新修改器列表'))
            msg_text = tr('<p>是否要更新修改器列表？</p><p>trainers_list.csv文件被用来储存与修改器相关的信息，其中也包括修改器的下载链接。你也可以通过手动修改trainers_list.csv文件中的数据来完善一些修改器的信息，但请注意数据格式是否正确。</p>') + tr('<p>最后更新：') + f'{self.update_time}</p>'
            msg_box.setText(msg_text)
            btn_yes = msg_box.addButton(tr('确定'), QMessageBox.ButtonRole.AcceptRole)
            btn_no = msg_box.addButton(tr('取消'), QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(btn_no)
            msg_box.exec()

        if (need_confirm and msg_box.clickedButton() == btn_yes) or not need_confirm:
            self.output_text_edit.show()
            update = UpdateDataRunnable(need_confirm)
            update.signals.update_signal.connect(self.append_output_text)
            update.signals.finished.connect(self.updateMessage)
            self.threadpool.start(update)

    def updateMessage(self, type, title, text):
        if type:
            self.getTrainersData()
            QMessageBox.information(self, title, text) 
        else:
            QMessageBox.critical(self, title, text)
        self.toggle_output_area(config.get('settings', 'debugMode') == 'true')

    def toggle_output_area(self, visible):
        if visible:
            self.output_text_edit.show()
        else:
            self.output_text_edit.hide()

    def importFiles(self):
        try:
            options = QFileDialog.Option.ReadOnly
            files, _ = QFileDialog.getOpenFileNames(self, tr("选择修改器文件"), "", "Executable Files (*.exe)", options=options)
            
            if files:
                target_dir = self.trainersPath
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                for file_path in files:
                    file_name = os.path.basename(file_path)
                    target_path = os.path.join(target_dir, file_name)
                    try:
                        shutil.copy(file_path, target_path)
                        self.append_output_text(f"<span style='color:green;'>[import]</span> {target_path}")
                    except Exception as e:
                        self.append_output_text(f"<span style='color:red;'>[error]</span> Failed to copy file '{file_name}': {str(e)}")
                self.loadTrainers()
                self.append_output_text(f"<span style='color:LightGreen;'>[success]</span> File imported successfully!")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def openDirectory(self):
        try:
            if os.path.exists(self.trainersPath) and os.path.isdir(self.trainersPath):
                os.startfile(self.trainersPath)
                self.append_output_text(f"<span style='color:LightSkyBlue;'>[open]</span> {self.trainersPath}")
            else:
                self.append_output_text(f"<span style='color:red;'>[error]</span> '{self.trainersPath}' does not exist.")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def importZipFiles(self):
        files, _ = QFileDialog.getOpenFileNames(self, tr("选择压缩包文件"), "", tr("压缩包 (*.zip *.rar)"))
        if files:
            cache_dir = os.path.join(os.getcwd(), 'cache')
            trainers_dir = os.path.join(os.getcwd(), 'trainers')
            os.makedirs(cache_dir, exist_ok=True)
            os.makedirs(trainers_dir, exist_ok=True)

            unrar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils', 'UnRAR.exe')
            rarfile.UNRAR_TOOL = unrar_path

            try:
                for fileName in files:
                    if fileName.endswith('.zip'):
                        with zipfile.ZipFile(fileName, 'r') as zip_ref:
                            zip_ref.extractall(cache_dir)
                    elif fileName.endswith('.rar'):
                        with rarfile.RarFile(fileName, 'r') as rar_ref:
                            rar_ref.extractall(cache_dir)
                    else:
                        self.append_output_text(f"<span style='color:red;'>[error]</span> File format error.")
                        return

                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        if file.endswith('.exe'):
                            os.rename(os.path.join(root, file), os.path.join(trainers_dir, file))
                            self.append_output_text(f"<span style='color:green;'>[import]</span> {os.path.join(trainers_dir, file)}")

                QMessageBox.information(self, tr("导入成功"), tr("<p>已从选择的压缩包导入修改器！</p><p><span style='color:red;'>但请注意，有些修改器可能需要额外的文件才能正确运行。</span></p>"))
                self.append_output_text(f"<span style='color:LightGreen;'>[success]</span> File imported successfully!")
                self.loadTrainers()
            except Exception as e:
                self.append_output_text(f"<span style='color:red;'>[error]</span> An error occurred while processing the archive: {str(e)}")
                QMessageBox.critical(self, tr("错误"), tr("处理压缩包时出现错误") + f": {e}")
            finally:
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for dir in dirs:
                        shutil.rmtree(os.path.join(root, dir))

    def openCsvFile(self, file_path):
        try:
            if os.path.exists(file_path):
                self.append_output_text(f"<span style='color:LightSkyBlue;'>[open]</span> {file_path}")
                QProcess.startDetached('notepad', [file_path]) 
            else:
                self.append_output_text(f"<span style='color:red;'>[error]</span> '{file_path}' cannot be found.")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def switchUI(self):
        action = self.sender()
        if action.text() == "Switch to English":
            config.set('settings', 'enableEnglishUI', 'true')
        else:
            config.set('settings', 'enableEnglishUI', 'false')
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    def switchTheme(self):
        if themeStyle == "dark":
            config.set('settings', 'themestyle', 'light')
        else:
            config.set('settings', 'themestyle', 'dark')
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)
        os.execl(sys.executable, sys.executable, *sys.argv)

    def downloadTool(self):
        action = self.sender()
        is_hidden = action.text() == tr("隐藏下载器")
        action.setText(tr("下载器") if is_hidden else tr("隐藏下载器"))
        config.set('settings', 'downloadToolIsHidden', str(is_hidden).lower())
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)

        self.lineEdit2.setVisible(not self.lineEdit2.isVisible())
        self.listWidgetRight.setVisible(not self.listWidgetRight.isVisible())

    def toggleTranslationSearch(self):
        action = self.sender()
        is_hidden = action.text() == tr("隐藏查找翻译")
        action.setText(tr("查找翻译") if is_hidden else tr("隐藏查找翻译"))
        config.set('settings', 'toggleTranslationSearchIsHidden', str(is_hidden).lower())
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)

        self.lineEdit3.setVisible(not self.lineEdit3.isVisible())
        self.listWidgetName.setVisible(not self.listWidgetName.isVisible())

    def translationFileName(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr('翻译修改器文件名'))
        msg_text = tr('<p>确定要翻译已有修改器的文件名？</p><p><span style="color:red;">此操作不可逆，且可能出现翻译错误。</span></p><p>翻译需要一些时间，画面可能会卡住，请耐心等待。</p>')
        msg_box.setText(msg_text)
        btn_yes = msg_box.addButton(tr('确定'), QMessageBox.ButtonRole.AcceptRole)
        btn_no = msg_box.addButton(tr('取消'), QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(btn_no)
        msg_box.exec()

        try:
            if msg_box.clickedButton() == btn_yes:
                for file_name in os.listdir(self.trainersPath):
                    if file_name.endswith(".exe"):
                        file_path = os.path.join(self.trainersPath, file_name)
                        base_name = os.path.splitext(file_name)[0]
                        normalized_name = extract_game_name(base_name)
                        name_suffix = base_name.split(normalized_name)[-1]
                        game_name_mapping = {
                            'Gui Gu Ba Huang': 'Tale of Immortal',
                            'Mi Chang Sheng': 'MCS',
                        }
                        normalized_name = game_name_mapping.get(normalized_name, normalized_name)

                        max_similarity = 0
                        best_match = None
                        for name_data in self.names_data:
                            sim = similarity(normalized_name.lower(), name_data["en_name"].lower())
                            if sim > max_similarity and sim > 0.8:
                                max_similarity = sim
                                best_match = name_data

                        if best_match:
                            new_file_name = f"{best_match['zh_name']}{name_suffix}.exe"
                            new_file_path = os.path.join(self.trainersPath, new_file_name)
                            os.rename(file_path, new_file_path)
                            self.append_output_text(f"<span style='color:LightSkyBlue;'>[rename]</span> '{file_name}' -> '{new_file_name}'")
                        else:
                            self.append_output_text(f"<span style='color:red;'>[rename]</span> No match found for '{file_name}'")
                self.append_output_text(f"<span style='color:LightGreen;'>[success]</span> File names translation completed!")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")
        finally:
            self.loadTrainers()

    def showAboutDialog(self):
        about_text = (f"<h1>Game Trainer Manager {self.version_number}</h1><p>{tr('项目贡献者：')}<a href='https://space.bilibili.com/2838092'>鸦无量</a></p><p>{tr('项目地址：')}</p><p><a href='https://github.com/Karasukaigan/game-trainer-manager'>Karasukaigan/game-trainer-manager(GitHub)</a></p>" +
                      tr("<h2>免责声明</h2>"
                      "<p>本项目为玩家自发制作，与FLiNG Trainer无关。其设计目的是用于管理包括但不限于FLiNG Trainer制作的任何.exe格式的游戏修改器文件。本软件完全免费且开源，请勿将其用于商业用途。</p>"
                      "<p>使用本软件所造成的任何损失，软件开发者概不负责。本软件尊重FLiNG Trainer等游戏修改器制作方的版权，不会对游戏修改器文件进行除修改文件名之外的任何修改，仅提供下载、保存、删除等管理功能。</p>"
                      "<p>此外，用户应自行承担下载和使用第三方游戏修改器所带来的风险。请确保您在使用修改器时遵守相关游戏的使用条款和服务协议。对于因违反游戏公司政策而导致的任何后果，开发者不承担责任。</p>"
                      "<p>本软件严格禁止用于任何非法用途，包括但不限于违反游戏公司政策、作弊、破坏游戏平衡等行为。用户在使用本软件时应当遵守相关法律法规和游戏公司政策，以确保公平和合法的游戏环境。</p>"
        ))
        message_box = QMessageBox(self)
        message_box.setWindowTitle(tr("关于Game Trainer Manager"))
        message_box.setIconPixmap(QPixmap(self.windowIcon().pixmap(100, 200)))
        message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        message_box.button(QMessageBox.StandardButton.Ok).setText(tr("我已知晓"))

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(332, 500)
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)  # 设置为富文本格式
        label.setText(about_text)
        label.setOpenExternalLinks(True) 
        label.setWordWrap(True)
        scroll_area.setWidget(label)
        scroll_area.setStyleSheet('''
            QLabel {
                padding: 0;
                border: none;
            }
        ''')
        message_box.layout().addWidget(scroll_area, 1, 1, 1, 1)

        message_box.exec()
    
    def openUrl(self, url):
        try:
            webbrowser.open(url)
            self.append_output_text(f"<span style='color:LightSkyBlue;'>[open]</span> {url}")
        except Exception as e:
            self.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")

    def append_output_text(self, text):
        self.output_text_edit.appendHtml(text)
