import re, csv, os
from bs4 import BeautifulSoup

def extract_game_name(title):
    pattern = re.compile(
        r'( v\d[\d\.\-]*.* Trainer.*$)|'
        r'( Plus \d+ Trainer.*$)|'
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

def preprocess_title(title):
    if '.v' in title:
        title = title.split('.v')[0].replace('.', ' ')
    if '.Plus' in title:
        title = title.split('.Plus')[0].replace('.', ' ')
    title = title.replace('_', ': ')
    return title

def get_game_trainers(file_path):
    game_trainers = []
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
        table = soup.find('table', class_='files')
        if table:
            for li in table.find_all("td"):
                a_element = li.find("a")
                if a_element:
                    game_name = preprocess_title(extract_game_name(a_element.text.strip()))
                    trainer_name = a_element.text.strip()
                    download_url = a_element["href"]
                    game_trainers.append({"game_name": game_name, "trainer_name": trainer_name, "download_url": download_url})
    return game_trainers

def save_list_to_csv(file_name, game_trainers):
    with open(file_name, 'w', encoding='utf-8', newline='') as csvfile:
        fieldnames = ['game_name', 'trainer_name', 'download_url']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(game_trainers)

if __name__ == "__main__":
    url = 'https://archive.flingtrainer.com/'
    html_file_path = 'FLiNG Trainers Archive.html'
    game_trainers = get_game_trainers(html_file_path)
    save_list_to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "trainers_list_old.csv"), game_trainers)
