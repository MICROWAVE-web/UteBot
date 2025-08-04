import os
import sys
import threading
import time
from datetime import timedelta, datetime

import investpy
import pytz
from PyQt5 import QtCore
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QGroupBox, QHBoxLayout, QSpinBox, QDialog, QCheckBox, QDialogButtonBox

from programm_files import save_news, load_additional_settings_data
from themes import light_theme, dark_theme


def tr(text):
    return QCoreApplication.translate("MainWindow", text, "MainWindow")


class NewsUpdater:
    """Класс для периодического обновления новостей"""

    def __init__(self, main_window, language):
        self.main_window = main_window
        self.language = language

        self.running = True
        self.update_interval = 60  # секунд
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()


    def run(self):
        """Основной цикл обновления новостей"""
        while self.running:
            try:
                # Проверяем, нужно ли обновить новости
                # news_settings = load_news_settings()
                if 1:
                    # Загружаем только новые новости
                    now = datetime.now(pytz.timezone('Etc/GMT-3'))
                    start_date = now.strftime("%d/%m/%Y")
                    end_date = (now + timedelta(days=1)).strftime("%d/%m/%Y")

                    # Получаем только сегодняшние и завтрашние новости
                    calendar = investpy.economic_calendar(
                        time_zone="GMT +3:00",
                        from_date=start_date,
                        to_date=end_date,
                        language=self.language
                    )
                    # Преобразуем в список словарей
                    new_news = []
                    for _, row in calendar.iterrows():
                        if ':' not in row['time']:
                            continue
                        new_news.append({
                            'id': row['id'],
                            'date': row['date'],
                            'time': row['time'],
                            'importance': row['importance'],
                            'currency': row['currency'],
                            'event': row['event'],
                            'before': 0,
                            'after': 0
                        })

                    # Обновляем новости
                    save_news(new_news)
                    # self.main_window.updateNewsTable(new_news)

                # Ждем до следующего обновления
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Ошибка обновления новостей: {e}")
                time.sleep(10)  # Ждем 10 секунд после ошибки

    def stop(self):
        """Останавливает обновление новостей"""
        self.running = False
        self.thread.join(timeout=1)


class NewsFilterDialog(QDialog):
    """Диалог настройки новостного фильтра"""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        if getattr(sys, 'frozen', False):
            applicationPath = sys._MEIPASS
        elif __file__:
            applicationPath = os.path.dirname(__file__)
        icon_path = os.path.join(applicationPath, 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(tr("Настройка новостного фильтра"))
        self.setMinimumWidth(400)

        self.translator = QtCore.QTranslator()

        layout = QVBoxLayout(self)

        # Настройки волатильности
        layout.addWidget(QLabel(tr("Укажите промежутки времени в минутах для фильтрации новостных событий:")))

        # Низкая волатильность
        low_group = QGroupBox(tr("Низкая волатильность"))
        low_layout = QHBoxLayout(low_group)

        low_layout.addWidget(QLabel(tr("Время До:")))
        self.low_before = QSpinBox()
        self.low_before.setRange(0, 1440)
        self.low_before.setValue(settings.get('low_before', 0))
        low_layout.addWidget(self.low_before)

        low_layout.addWidget(QLabel(tr("Время После:")))
        self.low_after = QSpinBox()
        self.low_after.setRange(0, 1440)
        self.low_after.setValue(settings.get('low_after', 0))
        low_layout.addWidget(self.low_after)

        layout.addWidget(low_group)

        # Средняя волатильность
        med_group = QGroupBox(tr("Средняя волатильность"))
        med_layout = QHBoxLayout(med_group)

        med_layout.addWidget(QLabel(tr("Время До:")))
        self.med_before = QSpinBox()
        self.med_before.setRange(0, 1440)
        self.med_before.setValue(settings.get('med_before', 0))
        med_layout.addWidget(self.med_before)

        med_layout.addWidget(QLabel(tr("Время После:")))
        self.med_after = QSpinBox()
        self.med_after.setRange(0, 1440)
        self.med_after.setValue(settings.get('med_after', 0))
        med_layout.addWidget(self.med_after)

        layout.addWidget(med_group)

        # Высокая волатильность
        high_group = QGroupBox(tr("Высокая волатильность"))
        high_layout = QHBoxLayout(high_group)

        high_layout.addWidget(QLabel(tr("Время До:")))
        self.high_before = QSpinBox()
        self.high_before.setRange(0, 1440)
        self.high_before.setValue(settings.get('high_before', 0))
        high_layout.addWidget(self.high_before)

        high_layout.addWidget(QLabel(tr("Время После:")))
        self.high_after = QSpinBox()
        self.high_after.setRange(0, 1440)
        self.high_after.setValue(settings.get('high_after', 0))
        high_layout.addWidget(self.high_after)

        layout.addWidget(high_group)

        # Чекбоксы
        self.only_currency_cb = QCheckBox(tr("Только основанные на валюте, затронутой новостями"))
        self.only_currency_cb.setChecked(settings.get('only_currency', False))
        layout.addWidget(self.only_currency_cb)

        self.reverse_filter_cb = QCheckBox(tr("Обратный новостной фильтр (торговля на новостях)"))
        self.reverse_filter_cb.setChecked(settings.get('reverse_filter', False))
        layout.addWidget(self.reverse_filter_cb)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        ok_button = buttons.button(QDialogButtonBox.Ok)
        ok_button.setText(tr("Ок"))
        ok_button.setStyleSheet("""
        QPushButton {
            background-color: rgb(83, 140, 85);
            color: white;
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        }

        QPushButton:hover {
            background-color: rgb(73, 120, 75); /* чуть темнее */
        }

        QPushButton:pressed {
            background-color: rgb(63, 100, 65); /* еще темнее при нажатии */
            padding-top: 9px;
            padding-bottom: 7px;
        }  
        """)
        ok_button.clicked.connect(self.accept)

        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        cancel_button.setText(tr("Отмена"))
        cancel_button.setStyleSheet("""
        QPushButton {
            background-color: #a83e3e;
            color: white;
            border-radius: 5px;
            padding: 8px;
            font-size: 12px;
        }

        QPushButton:hover {
            background-color: #922f2f; /* чуть темнее */
        }

        QPushButton:pressed {
            background-color: #7a2424; /* ещё темнее при нажатии */
            padding-top: 9px;
            padding-bottom: 7px;
        }     
        """)
        cancel_button.clicked.connect(self.reject)

        layout.addWidget(buttons)

        self.setStyleSheet("""
                    border-radius: 5px;
                    padding: 5px;
                    font-size: 12px;
                """)

        # Пример, если хранишь тему в настройках
        settings = load_additional_settings_data()
        self.theme = settings.get("theme", "dark")

        if self.theme == 'light':
            style_str = light_theme
        else:
            style_str = dark_theme

        # Применяем стили ко всему приложению
        self.setStyleSheet(style_str)

    def get_settings(self):
        """Возвращает текущие настройки"""
        return {
            'low_before': self.low_before.value(),
            'low_after': self.low_after.value(),
            'med_before': self.med_before.value(),
            'med_after': self.med_after.value(),
            'high_before': self.high_before.value(),
            'high_after': self.high_after.value(),
            'only_currency': self.only_currency_cb.isChecked(),
            'reverse_filter': self.reverse_filter_cb.isChecked()
        }
