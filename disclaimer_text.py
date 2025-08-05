import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit
)
from PyQt5.QtCore import Qt, QUrl, QCoreApplication
from PyQt5.QtGui import QDesktopServices, QCursor, QIcon
from PyQt5 import QtCore

from programm_files import load_additional_settings_data
from themes import light_theme, dark_theme


def tr(text):
    return QCoreApplication.translate("MainWindow", text, "MainWindow")


class DisclaimerWindow(QWidget):
    def __init__(self):
        super().__init__()
        if getattr(sys, 'frozen', False):
            applicationPath = sys._MEIPASS
        elif __file__:
            applicationPath = os.path.dirname(__file__)
        icon_path = os.path.join(applicationPath, 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setObjectName("disclaimerWindow")
        self.setWindowTitle(tr("Отказ от ответственности"))
        self.setMinimumSize(500, 350)
        self.setup_ui()

        # Пример, если хранишь тему в настройках
        settings = load_additional_settings_data()
        self.theme = settings.get("theme", "dark")

        if self.theme == 'light':
            style_str = light_theme
        else:
            style_str = dark_theme

        self.translator = QtCore.QTranslator()

        # Применяем стили ко всему приложению
        self.setStyleSheet(style_str)

    def setup_ui(self):
        layout = QVBoxLayout()

        # Текст отказа
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setHtml(tr("""<b>Отказ от ответственности</b><br><br>
Настоящим сообщаем, что предоставляемая услуга является автоматической торговой системой, 
и результаты её работы не гарантируют прибыль. Торговля на финансовых рынках связана с высоким уровнем риска, 
и возможны как значительные прибыли, так и убытки.<br><br>
Пользователь полностью осознает и принимает на себя все риски, связанные с использованием данного бота. 
Администрация не несет ответственности за любые финансовые потери или убытки, 
возникшие в результате использования данной автоматической системы.<br><br>
Перед началом использования рекомендуется ознакомиться с условиями и проверить 
используемые торговые системы на учебном счёте.<br><br>
Использование бота означает согласие с данным отказом от ответственности."""))
        layout.addWidget(self.text)

        # Нижняя панель с кнопкой OK и ссылкой
        bottom_layout = QHBoxLayout()

        # self.link = QLabel('<a href="#">Отказ от ответственности / Disclaimer</a>')
        # self.link.setOpenExternalLinks(False)
        # self.link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        # self.link.setCursor(QCursor(Qt.PointingHandCursor))
        # self.link.linkActivated.connect(self.show_full_disclaimer)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.close)

        # bottom_layout.addWidget(self.link, alignment=Qt.AlignLeft)
        bottom_layout.addStretch()
        bottom_layout.addWidget(ok_button, alignment=Qt.AlignRight)

        layout.addLayout(bottom_layout)
        self.setLayout(layout)


def main():
    app = QApplication(sys.argv)
    window = DisclaimerWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
