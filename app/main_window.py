from PySide6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QMenuBar, QMenu, QLineEdit, QHBoxLayout, QVBoxLayout, QWidget, QFileDialog, QLabel, QScrollArea, QDialog, QPushButton
from PySide6.QtCore import Qt, QProcess, Signal, QThreadPool, QRunnable, QObject, QTimer, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from app.config import *
from app.utils.helpers import *
from app.widgets.custom_list import *
from app.widgets.download_list import *
from app.widgets.name_list import *
import csv, shutil, sys
import zipfile, rarfile
import requests
from datetime import datetime, timedelta
import app.tools as tools

class UpdateDataSignals(QObject):
    update_signal = Signal(str, str)
    finished = Signal(bool, str, str)
    restart_signal = Signal()

class UpdateDataRunnable(QRunnable):
    def __init__(self, need_confirm):
        super().__init__()
        self.signals = UpdateDataSignals()
        self.need_confirm = need_confirm
        
    def run(self):
        try:
            resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
            proxies_path = os.path.join(resources_path, 'proxies.txt')
            base_urls = []
            try:
                with open(proxies_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            base_urls.append(line)
            except FileNotFoundError:
                base_urls = [
                    'https://raw.githubusercontent.com/Karasukaigan/game-trainer-manager/main/app/resources/',
                ]
            downloads = ["trainers_list.csv", "game_names_merged.csv", "abbreviation.csv"]
            for download in downloads:
                downloaded = False
                for base_url in base_urls:
                    download_url = base_url + download
                    local_filename = os.path.join(resources_path, download)
                    self.signals.update_signal.emit(f"<span style='color:yellow;'>[download]</span> {download_url}", "info")
                    try:
                        response = requests.get(download_url, timeout=6)
                        if response.status_code == 200:
                            with open(local_filename, 'wb') as f:
                                f.write(response.content)
                            self.signals.update_signal.emit(f"<span style='color:yellow;'>[save]</span> Download successful : {local_filename}", "info")
                            downloaded = True
                            break
                        else:
                            raise requests.exceptions.RequestException(f"HTTP {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        self.signals.update_signal.emit(f"Network request error : {str(e)} on {download_url}", "error")
                if not downloaded:
                    raise Exception(f"Failed to download {download} from all URLs")
            self.signals.update_signal.emit(f"Data related to the trainers has been updated!", "success")
            if self.need_confirm:
                self.signals.finished.emit(True, tr("更新成功"), tr("修改器相关数据更新完成。"))
            self.signals.restart_signal.emit()
            return
        except requests.exceptions.RequestException as e:
            self.signals.update_signal.emit(f"Network request error : {str(e)}", "error")
            if self.need_confirm:
                self.signals.finished.emit(False, tr("更新失败"), tr("网络错误，请稍后再试。"))
        except Exception as e:
            self.signals.update_signal.emit(f"An unexpected error occurred: {str(e)}", "error")
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
        self.download_dir = downloadDir
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._checkDownloadDir)
        self._monitor_snapshot = set()
        self._monitor_game_name = ""
        self._monitor_count = 0

        self.initUI()
        self.loadTrainers()
        self.auto_update(updateTime)
        self.getTrainersData()

    def auto_update(self, last_update_time):
        last_update_datetime = datetime.strptime(last_update_time, "%Y-%m-%d")
        current_date = datetime.now()
        delta = current_date - last_update_datetime
        if delta > timedelta(days=2):
            self.append_log(f"More than two days have passed since {last_update_time}, an update is needed.", "info", "red")
            try:
                self.updateData(False)
                config.set('settings', 'updatetime', current_date.strftime("%Y-%m-%d"))
                with open(self.config_path, 'w') as configfile:
                    config.write(configfile)
                return current_date.strftime("%Y-%m-%d")
            except Exception as e:
                self.append_log(f"Automatic update failed : {e}", "error")
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
        setDownloadDirAction = fileMenu.addAction(tr("设置下载目录"))
        setDownloadDirAction.triggered.connect(self.setDownloadDir)
        fileMenu.addSeparator()
        updateAction = fileMenu.addAction(tr("更新修改器列表"))
        editProxiesAction = fileMenu.addAction(tr("修改GitHub文件加速"))
        openListAction = fileMenu.addAction(tr("打开修改器列表"))
        openOldListAction = fileMenu.addAction(tr("打开旧修改器列表"))
        updateAction.triggered.connect(lambda: self.updateData(True))
        editProxiesAction.triggered.connect(lambda: self.openCsvFile(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'proxies.txt')))
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
        switchThemeAction.triggered.connect(self.switchTheme)
        debugAction = QAction(tr("关闭Debug模式") if config.get('settings', 'debugMode') == 'true' else tr("Debug模式"), self)
        debugAction.triggered.connect(self.toggleDebugMode)
        setMenu.addAction(debugAction)
        switchUIAction = setMenu.addAction("Switch to English")
        switchUIAction.triggered.connect(self.switchUI)
        menuBar.addMenu(setMenu)

        helpMenu = QMenu(tr("帮助"), self)
        openFLiNGAction = helpMenu.addAction(tr("打开风灵月影官网"))
        openArchiveLinkAction = helpMenu.addAction(tr("打开旧修改器列表(2012~2019.05)"))
        openSteamAction = helpMenu.addAction(tr("打开Steam官网"))
        openCELinkAction = helpMenu.addAction(tr("打开Cheat Engine官网"))
        helpMenu.addSeparator()
        openGithubAction = helpMenu.addAction(tr("打开GitHub项目页面"))
        aboutAction = helpMenu.addAction(tr("关于"))
        openFLiNGAction.triggered.connect(lambda: self.openUrl("https://flingtrainer.com/all-trainers/"))
        openArchiveLinkAction.triggered.connect(lambda: self.openUrl("https://archive.flingtrainer.com/"))
        openSteamAction.triggered.connect(lambda: self.openUrl("https://store.steampowered.com/"))
        openCELinkAction.triggered.connect(lambda: self.openUrl("https://www.cheatengine.org/"))
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

        self.append_log(f"The main window has been loaded.")
        
        if isFirstStart == 'true':
            self.showAboutDialog()
            config.set('settings', 'isFirstStart', 'false')
            with open(self.config_path, 'w') as configfile:
                config.write(configfile)
    
    def loadTrainers(self):
        """加载已导入的修改器"""
        try:
            if not os.path.exists(self.trainersPath):
                os.makedirs(self.trainersPath)

            self.trainers = []
            self.listWidgetLeft.clear()

            items_to_add = []

            for root, _, files in os.walk(self.trainersPath):
                for file in files:
                    if file.endswith(".exe"):
                        full_path = os.path.join(root, file)
                        self.trainers.append(full_path)
                        items_to_add.append(file.split('.exe')[0])

            for item in items_to_add:
                self.listWidgetLeft.addItem(item)

            pinned = self.listWidgetLeft._read_pinned()
            existing_names = set(items_to_add)
            for name in reversed(pinned):
                if name not in existing_names:
                    continue
                items = self.listWidgetLeft.findItems(name, Qt.MatchFlag.MatchExactly)
                if items:
                    item = items[0]
                    row = self.listWidgetLeft.row(item)
                    if row != 0:
                        taken = self.listWidgetLeft.takeItem(row)
                        self.listWidgetLeft.insertItem(0, taken)

            valid_pinned = [name for name in pinned if name in existing_names]
            if len(valid_pinned) != len(pinned):
                self.listWidgetLeft._write_pinned(valid_pinned)

            self.listWidgetLeft._update_pinned_style()
            self.append_log(f"The list of trainers has been loaded.")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")
            
    def getTrainersData(self):
        """获取修改器数据"""
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
            self.append_log(f"Data for all trainers has been loaded.")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")
    
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
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")

    
    def read_abbreviation_from_csv(self, file_path):
        """获取修改器别名数据"""
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
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")

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
            self.append_log(f"Query results have been obtained.", "success")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")

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
            update.signals.update_signal.connect(self.append_log)
            update.signals.finished.connect(self.updateMessage)
            update.signals.restart_signal.connect(self.restartApplication)
            self.threadpool.start(update)

    def updateMessage(self, type, title, text):
        if type:
            self.getTrainersData()
            QMessageBox.information(self, title, text) 
        else:
            QMessageBox.critical(self, title, text)
        self.toggle_output_area(config.get('settings', 'debugMode') == 'true')

    def restartApplication(self):
        QProcess.startDetached(sys.executable, sys.argv)
        sys.exit(0)

    def toggle_output_area(self, visible):
        if visible:
            self.output_text_edit.show()
        else:
            self.output_text_edit.hide()

    def importFiles(self):
        self.stopDownloadMonitor()
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
                        self.append_log(f"{target_path}", "import")
                    except Exception as e:
                        self.append_log(f"Failed to copy file '{file_name}': {str(e)}", "error")
                self.loadTrainers()
                self.append_log(f"File imported successfully!", "success")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")

    def openDirectory(self):
        try:
            if os.path.exists(self.trainersPath) and os.path.isdir(self.trainersPath):
                os.startfile(self.trainersPath)
                self.append_log(f"{self.trainersPath}", "open")
            else:
                self.append_log(f"'{self.trainersPath}' does not exist.", "error")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")

    def importZipFiles(self):
        self.stopDownloadMonitor()
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
                        self.append_log(f"File format error.", "error")
                        return

                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        if file.endswith('.exe'):
                            os.rename(os.path.join(root, file), os.path.join(trainers_dir, file))
                            self.append_log(f"{os.path.join(trainers_dir, file)}", "import")

                QMessageBox.information(self, tr("导入成功"), tr("<p>已从选择的压缩包导入修改器！</p><p><span style='color:red;'>但请注意，有些修改器可能需要额外的文件才能正确运行。</span></p>"))
                self.append_log(f"File imported successfully!", "success")
                self.loadTrainers()
            except Exception as e:
                self.append_log(f"An error occurred while processing the archive: {str(e)}", "error")
                QMessageBox.critical(self, tr("错误"), tr("处理压缩包时出现错误") + f": {e}")
            finally:
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for dir in dirs:
                        shutil.rmtree(os.path.join(root, dir))

    def setDownloadDir(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("设置下载目录"))
        dialog.setMinimumWidth(500)
        if themeStyle == 'dark':
            dialog.setStyleSheet("QDialog { background-color: #1e1e1e; color: #d4d4d4; }")
        else:
            dialog.setStyleSheet("QDialog { background-color: #ffffff; color: #333333; }")
        layout = QVBoxLayout(dialog)

        path_layout = QHBoxLayout()
        line_edit = QLineEdit(os.path.expandvars(self.download_dir))
        folder_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="''' + ('#d4d4d4' if themeStyle == 'dark' else '#333333') + '''"><path d="M12.4142 5H21C21.5523 5 22 5.44772 22 6V20C22 20.5523 21.5523 21 21 21H3C2.44772 21 2 20.5523 2 20V4C2 3.44772 2.44772 3 3 3H10.4142L12.4142 5ZM20 11H4V19H20V11ZM20 9V7H11.5858L9.58579 5H4V9H20Z"></path></svg>'''
        renderer = QSvgRenderer(QByteArray(folder_svg.encode('utf-8')))
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        browse_btn = QPushButton()
        browse_btn.setIcon(QIcon(pixmap))
        browse_btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 4px; }")
        browse_btn.clicked.connect(lambda: line_edit.setText(
            QFileDialog.getExistingDirectory(dialog, tr("选择下载目录"), line_edit.text())))
        path_layout.addWidget(line_edit)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(tr("确定"))
        cancel_btn = QPushButton(tr("取消"))
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.download_dir = line_edit.text()
            config.set('settings', 'downloaddir', self.download_dir)
            with open(self.config_path, 'w') as configfile:
                config.write(configfile)
            self.append_log(f"Download directory set to: {self.download_dir}", "save")

    def startDownloadMonitor(self, game_name):
        self.stopDownloadMonitor()
        download_path = os.path.expandvars(self.download_dir)
        if not os.path.isdir(download_path):
            self.append_log(f"Download directory does not exist: {download_path}", "warning")
            return
        self._monitor_snapshot = set(os.listdir(download_path))
        self._monitor_game_name = game_name
        self._monitor_count = 0
        self._monitor_timer.start(1000)
        self.append_log(f"Started monitoring download directory for: {game_name}", "info")

    def stopDownloadMonitor(self):
        if self._monitor_timer.isActive():
            self._monitor_timer.stop()
            self.append_log("Download monitoring stopped.", "info")

    def _autoImportFile(self, file_path, filename):
        ext = os.path.splitext(filename)[1].lower()
        trainers_dir = os.path.join(os.getcwd(), 'trainers')
        os.makedirs(trainers_dir, exist_ok=True)

        if ext == '.exe':
            target_path = os.path.join(trainers_dir, filename)
            shutil.copy(file_path, target_path)
            self.append_log(f"Auto-imported: {filename}", "import")
            self.loadTrainers()
            self.append_log(f"Auto-import completed!", "success")
        elif ext in ('.zip', '.rar'):
            cache_dir = os.path.join(os.getcwd(), 'cache')
            os.makedirs(cache_dir, exist_ok=True)
            unrar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils', 'UnRAR.exe')
            rarfile.UNRAR_TOOL = unrar_path
            try:
                if ext == '.zip':
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(cache_dir)
                else:
                    with rarfile.RarFile(file_path, 'r') as rar_ref:
                        rar_ref.extractall(cache_dir)
                for root, _, files in os.walk(cache_dir):
                    for f in files:
                        if f.endswith('.exe'):
                            src = os.path.join(root, f)
                            dst = os.path.join(trainers_dir, f)
                            shutil.copy(src, dst)
                            self.append_log(f"Auto-imported: {f}", "import")
                self.loadTrainers()
                self.append_log(f"Auto-import completed!", "success")
            finally:
                for root, dirs, files in os.walk(cache_dir):
                    for f in files:
                        os.remove(os.path.join(root, f))
                    for d in dirs:
                        shutil.rmtree(os.path.join(root, d))
        else:
            self.append_log(f"Unsupported file type for auto-import: {filename}", "warning")

    def _checkDownloadDir(self):
        self._monitor_count += 1
        if self._monitor_count > 300:
            self._monitor_timer.stop()
            self.append_log("Download monitoring timed out after 300 seconds.", "warning")
            return

        download_path = os.path.expandvars(self.download_dir)
        if not os.path.isdir(download_path):
            return

        try:
            current_files = set(os.listdir(download_path))
        except PermissionError:
            return

        new_files = current_files - self._monitor_snapshot
        for filename in new_files:
            file_path = os.path.join(download_path, filename)
            if not os.path.isfile(file_path):
                continue
            if filename.lower().endswith(('.crdownload', '.part', '.tmp')):
                continue
            name_only = os.path.splitext(filename)[0]
            extracted = extract_game_name(name_only)
            sim = similarity(extracted, self._monitor_game_name)
            if sim > 0.8:
                self.append_log(f"Detected new file: {filename} (similarity: {sim:.2f})", "info")
                self._autoImportFile(file_path, filename)
                self._monitor_timer.stop()
                return

    def openCsvFile(self, file_path):
        try:
            if os.path.exists(file_path):
                self.append_log(f"{file_path}", "open")
                QProcess.startDetached('notepad', [file_path]) 
            else:
                self.append_log(f"'{file_path}' cannot be found.", "error")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")

    def switchUI(self):
        action = self.sender()
        if action.text() == "Switch to English":
            config.set('settings', 'enableEnglishUI', 'true')
        else:
            config.set('settings', 'enableEnglishUI', 'false')
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)
        QProcess.startDetached(sys.executable, sys.argv)
        sys.exit(0)
        
    def switchTheme(self):
        if themeStyle == "dark":
            config.set('settings', 'themestyle', 'light')
        else:
            config.set('settings', 'themestyle', 'dark')
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)
        QProcess.startDetached(sys.executable, sys.argv)
        sys.exit(0)

    def toggleDebugMode(self):
        action = self.sender()
        is_debug = action.text() == tr("关闭Debug模式")
        config.set('settings', 'debugMode', str(not is_debug).lower())
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)
        action.setText(tr("Debug模式") if is_debug else tr("关闭Debug模式"))
        self.output_text_edit.setVisible(not is_debug)

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
                            self.append_log(f"'{file_name}' -> '{new_file_name}'", "rename")
                        else:
                            self.append_log(f"No match found for '{file_name}'", "error")
                self.append_log(f"File names translation completed!", "success")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")
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
            self.append_log(f"{url}", "open")
        except Exception as e:
            self.append_log(f"An unexpected error occurred: {str(e)}", "error")

    def append_log(self, text, tag="info", color=None):
        """
        输出日志

        参数:
            text (str): 日志文本内容。
            tag (str, optional): 信息类型标签，默认为"info"。
                常见标签包括:
                - "info": 普通信息 (颜色: LightGreen)
                - "success": 成功信息 (颜色: LightGreen)
                - "warning": 警告信息 (颜色: yellow)
                - "error": 错误信息 (颜色: red)
                - "download": 下载操作相关信息 (颜色: yellow)
                - "save": 保存操作相关信息 (颜色: yellow)
                - "import": 导入操作相关信息 (颜色: green)
                - "open": 打开操作相关信息 (颜色: LightSkyBlue)
                - "rename": 重命名操作相关信息 (颜色: LightSkyBlue)
                - "delete": 删除操作相关信息 (颜色: LightSkyBlue)
            color (str, optional): 指定文本颜色，如果提供则覆盖标签对应的颜色。
        """
        tag_colors = {
            "info": "LightGreen",
            "success": "LightGreen",
            "warning": "yellow",
            "error": "red",
            "download": "yellow",
            "save": "yellow",
            "import": "green",
            "open": "LightSkyBlue",
            "rename": "LightSkyBlue",
            "delete": "LightSkyBlue"
        }
        if not color:
            color = tag_colors.get(tag, "LightGreen")
        self.output_text_edit.appendHtml(f"<span style='color:{color};'>[{tag}]</span> {text}")
