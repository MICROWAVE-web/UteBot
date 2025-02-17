import os
import json
from platformdirs import *

appname = "UteBot"

appauthor = "UteBot"

data_dir = f'{user_data_dir(appname, appauthor)}'
log_dir = f'{user_log_dir(appname, appauthor)}'


def init_dirs():
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)


def save_money_management_data(mm_data):
    with open(fr'{data_dir}\mm_data.log', 'w', encoding='utf-8') as f:
        json.dump(mm_data, f, indent=4, ensure_ascii=False)


def load_money_management_data():
    try:
        with open(fr'{data_dir}\mm_data.log', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_statistic_data():
    pass


def load_statistic_data():
    pass


def save_auth_data(auth_data):
    with open(fr'{data_dir}\auth_data.log', 'w', encoding='utf-8') as f:
        json.dump(auth_data, f, indent=4, ensure_ascii=False)


def load_auth_data():
    try:
        with open(fr'{data_dir}\auth_data.log', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

if __name__ == '__main__':
    init_dirs()
