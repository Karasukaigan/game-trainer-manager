import configparser
import os

config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', "config.ini")
config = configparser.ConfigParser()
config.read(config_file_path)
version_number = config.get('settings', 'versionNumber').upper()
isFirstStart = config.get('settings', 'isFirstStart')
trainersPath = config.get('settings', 'trainersPath')
enableEnglishUI = config.get('settings', 'enableEnglishUI')

trainers_data = []
