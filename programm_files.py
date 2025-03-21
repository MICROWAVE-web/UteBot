import json
import os
import sys
import uuid
from pathlib import Path

from platformdirs import *

appname = "UTEConnect"

appauthor = "UTEConnect"

# Получаем путь к текущему исполняемому файлу (если .exe, то он будет корректным)
EXE_PATH = Path(sys.argv[0]).resolve()
print(EXE_PATH)

# Определяем путь к файлу привязки в конфигурационной директории пользователя
CONFIG_DIR = Path(user_data_dir(appname, appauthor))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "instances.json"


def load_instances():
    """Загружает привязки экземпляров из файла."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass  # Если файл повреждён, игнорируем его

    return {}


def save_instances(instances):
    """Сохраняет обновлённые привязки экземпляров."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(instances, f, indent=4)


def get_or_create_instance_directory():
    """Определяет уникальную папку для данного экземпляра программы."""
    instances = load_instances()
    exe_key = str(EXE_PATH)  # Уникальный ключ для текущего .exe

    if exe_key in instances:
        instance_dir = Path(instances[exe_key])
        if instance_dir.exists():
            return instance_dir  # Возвращаем привязанную папку

    # Если привязки нет, создаём новую папку
    new_instance_dir = CONFIG_DIR / f"instance_{uuid.uuid4().hex}"
    new_instance_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем привязку
    instances[exe_key] = str(new_instance_dir)
    save_instances(instances)

    return new_instance_dir


def init_dirs():
    print(data_dir, log_dir)
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


def save_statistic_data(statistic_data):
    with open(fr'{data_dir}\statistic_data.json', 'w', encoding='utf-8') as f:
        json.dump(statistic_data, f, indent=4, ensure_ascii=False)


def load_statistic_data():
    try:
        with open(fr'{data_dir}\statistic_data.json', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "summary": {
            },
            "trades": [],
        }

def save_auth_data(auth_data):
    with open(fr'{data_dir}\auth_data.log', 'w', encoding='utf-8') as f:
        json.dump(auth_data, f, indent=4, ensure_ascii=False)


def load_auth_data():
    try:
        with open(fr'{data_dir}\auth_data.log', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


data_dir = get_or_create_instance_directory()
log_dir = f'{user_log_dir(appname, appauthor)}'

if __name__ == '__main__':
    init_dirs()

    # Получаем или создаём уникальную папку
    instance_directory = get_or_create_instance_directory()

    print(f"Этот экземпляр использует папку: {instance_directory}")
