import difflib, csv, re, os, gettext
from app.config import *

def load_translation():
    global enableEnglishUI
    if enableEnglishUI == 'true':
        lang = gettext.translation('game_trainer_manager', localedir=os.path.join(os.path.dirname(__file__), '..', '..', 'translations'), languages=['en'])
        lang.install()

def similarity(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def read_csv(file_name):
        with open(file_name, 'r', encoding='utf-8') as csvfile:
            return [row for row in csv.DictReader(csvfile)]
        
def contains_chinese(s):
        return re.search(u'[\u4e00-\u9fff]', s) is not None

def contains_japanese(s):
    return re.search(u'[\u3040-\u30ff]', s) is not None

def contains_english(s):
    return re.search(u'[a-zA-Z]', s) is not None

def extract_game_name(title):
    pattern = re.compile(
        r'( v\d[\d\.\-]*.* Trainer.*$)|'
        r'( v\d[\d\.\-]*.* MrAntiFun.*$)|'
        r'( Plus \d+ Trainer.*$)|'
        r'( Early Access Plus \d+ Trainer.*$)|'
        r'( Build \d[\d\.\-]*.* Trainer.*$)|'
        r'( \(.*?\) v\d[\d\.\-]*.* Trainer.*$)|'
        r'( Update \d[\d\-]*.* Trainer.*$)|'
        r'( \(Update \d+.*?\) Plus \d+ Trainer.*$)|'
        r'( v[\d\.\-]+.*$)|'
        r'( [\d\.\-]+-Update \d+.*? Trainer.*$)',
        re.IGNORECASE
    )
    game_name = re.sub(pattern, '', title)
    return game_name