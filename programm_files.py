import json
import logging
import os
import sys
import uuid
from pathlib import Path

from platformdirs import *

CURRENT_VERSION = '1.0.4'  # Текущая версия бота

appname = f"UTEConnect_{CURRENT_VERSION}"

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


def save_additional_settings_data(auth_data):
    try:
        with open(fr'{data_dir}\additional_settings_data.json', 'w', encoding='utf-8') as f:
            json.dump(auth_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving settings: {str(e)}")


"""
{
    "pairs": {
        "EURUSD": True,
        "GBPUSD": False,
        # ...
    },
    "schedule": {
        "Пн": {"enabled": True, "start": "09:00", "end": "23:59"},
        "Вт": {"enabled": True, "start": "09:00", "end": "17:00"},
        "Ср": {"enabled": False, "start": "00:00", "end": "00:00"},
        # ...
    }
}
"""


def load_additional_settings_data():
    try:
        if os.path.exists(fr'{data_dir}\\additional_settings_data.json'):
            with open(fr'{data_dir}\\additional_settings_data.json', "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Создаем настройки по умолчанию
            default_settings = {
                "pairs": {},
                "schedule": {
                    "Пн": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "Вт": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "Ср": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "Чт": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "Пт": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "Сб": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                    "Вс": {
                        "enabled": True,
                        "intervals": [
                            {"start": "00:00", "end": "23:59"},
                        ]
                    },
                }
            }
            save_additional_settings_data(default_settings)
            return default_settings
    except Exception as e:
        logging.error(f"Error loading settings: {str(e)}")
        return None


# Функции для работы с настройками новостей
def save_news_settings(settings):
    try:
        with open(fr"{data_dir}\news_settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения настроек новостей: {str(e)}")


def load_news_settings():
    try:
        if os.path.exists(fr"{data_dir}\news_settings.json"):
            with open(fr"{data_dir}\news_settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка загрузки настроек новостей: {str(e)}")
    return {}


# Функции для работы с настройками новостей
def save_news(news_dict):
    try:
        with open(fr"{data_dir}\news.json", "w", encoding="utf-8") as f:
            json.dump(news_dict, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения настроек новостей: {str(e)}")


def load_news():
    try:
        if os.path.exists(fr"{data_dir}\news.json"):
            with open(fr"{data_dir}\news.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка загрузки настроек новостей: {str(e)}")
    return {}


data_dir = get_or_create_instance_directory()
log_dir = f'{user_log_dir(appname, appauthor)}'

if __name__ == '__main__':
    init_dirs()

    # Получаем или создаём уникальную папку
    instance_directory = get_or_create_instance_directory()

    print(f"Этот экземпляр использует папку: {instance_directory}")
