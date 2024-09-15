import requests
import csv, os
from bs4 import BeautifulSoup
from retrying import retry
from typing import List, Dict

def fetch_game_trainers(main_window):
    url = "https://flingtrainer.com/all-trainers-a-z/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    main_window.append_output_text(f"<span style='color:LightSkyBlue;'>[get]</span> {url}")

    game_trainers = []
    for ul in soup.find_all("ul", class_="az-columns"):
        for li in ul.find_all("li"):
            a_element = li.find("a")
            trainer_name = a_element.text.strip()
            game_name = trainer_name.split(" Trainer")[0]
            trainer_url = a_element["href"]
            game_trainers.append({"game_name": game_name, "trainer_name": trainer_name,"trainer_url": trainer_url})
    
    return game_trainers

def save_list_to_csv(file_name, game_trainers):
    with open(file_name, 'w', encoding='utf-8', newline='') as csvfile:
        fieldnames = ['game_name', 'trainer_name', 'trainer_url', 'download_url']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(game_trainers)

@retry(stop_max_attempt_number=10, wait_fixed=2000)
def fetch_page_content(trainer_url, headers):
    try:
        response = requests.get(trainer_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup
    except Exception as e:
        print(f"[error] {trainer_url} : {e}")
        raise e

def fetch_download_url(trainer_url):
    download_url = ''
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
    try:
        soup = fetch_page_content(trainer_url, headers)
    except Exception as e:
        print(f"[error] {trainer_url} : {e}")
        return download_url
    table = soup.find("table", class_="da-attachments-table")
    if table:
        tbody = table.find("tbody")
        first_a_element = tbody.find("a")
        if first_a_element:
            download_url = first_a_element["href"] 
    return download_url

def fetch_game_trainers_old(main_window) -> List[Dict]:
    trainers_data = []
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "trainers_list.csv"), mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                trainer_dict = {
                    'game_name': row[0],
                    'trainer_name': row[1],
                    'trainer_url': row[2],
                    'download_url': row[3]
                }
                trainers_data.append(trainer_dict)
    except Exception as e:
        main_window.append_output_text(f"<span style='color:red;'>[error]</span> An unexpected error occurred: {str(e)}")
    return trainers_data

if __name__ == "__main__":
    pass
    # game_trainers = fetch_game_trainers()
    # game_trainers_old = fetch_game_trainers_old()
    # game_names_old = {trainer['game_name'] for trainer in game_trainers_old}
    # n = 0
    # for trainer in game_trainers:
    #     n += 1
    #     if trainer["game_name"] not in game_names_old:
    #         time.sleep(0.5)
    #         trainer["download_url"] = fetch_download_url(trainer["trainer_url"])
    #         game_trainers_old.append(trainer)
    #         print('(', n, '/', len(game_trainers), ')', '[add]', trainer)
    #     else:
    #         print('(', n, '/', len(game_trainers), ')', '[ok]', trainer)
    # save_list_to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "trainers_list.csv"), game_trainers_old)