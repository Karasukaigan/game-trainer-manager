import configparser
import os

config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', "config.ini")
config = configparser.ConfigParser(interpolation=None)
config.read(config_file_path)
version_number = config.get('settings', 'versionNumber').upper()
isFirstStart = config.get('settings', 'isFirstStart')
trainersPath = config.get('settings', 'trainersPath')
downloadDir = config.get('settings', 'downloaddir')
enableEnglishUI = config.get('settings', 'enableEnglishUI')
themeStyle = config.get('settings', 'themestyle')
updateTime = config.get('settings', 'updatetime')

trainers_data = []
