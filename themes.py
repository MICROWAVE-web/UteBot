# Файл themes.py с полным описанием всех стилей

dark_theme = """
    /* Основные стили */
    QMainWindow {
        background-color: rgb(13, 17, 48);
        color: white;
    }
    
    /* Всплывающее меню (ПКМ) */
    QMenu {
        background-color: rgb(18, 26, 61);
        color: white;
        border: 1px solid rgb(50, 50, 50);
        padding: 4px;
    }

    QMenu::item {
        background-color: transparent;
        padding: 6px 24px;
        margin: 2px 1px;
    }

    QMenu::item:selected {
        background-color: rgb(36, 52, 102);
        color: white;
    }

    QMenu::separator {
        height: 1px;
        background: rgb(80, 80, 80);
        margin: 4px 0;
    }

    QWidget {
        /* background-color: rgb(13, 17, 48);*/ 
        color: white;
        
    }
    
    QDialog {
        background-color: rgb(13, 17, 48);
        color: white;
    }

    QMessageBox {
        background-color: rgb(13, 17, 48);
        color: white;
    }
    

    /* Текст и метки */
    QLabel {
        color: white;
    }

    /* Кнопки */
    QPushButton {
        background-color: rgb(18, 26, 61);
        color: white;
        border-radius: 5px;
        padding: 8px;
        font-size: 12px;
    }

    QPushButton:hover {
        background-color: rgb(15, 22, 50);
    }

    QPushButton#startButton {
        background-color: rgb(83, 140, 85);
    }

    QPushButton#startButton:hover {
        background-color: rgb(73, 120, 75);
    }

    QPushButton#startButton:pressed {
        background-color: rgb(63, 100, 65);
        padding-top: 9px;
        padding-bottom: 7px;
    }

    QPushButton#stopButton {
        background-color: #a83e3e;
    }

    QPushButton#stopButton:hover {
        background-color: #922f2f;
    }

    QPushButton#stopButton:pressed {
        background-color: #7a2424;
        padding-top: 9px;
        padding-bottom: 7px;
    }

    /* Поля ввода */
    QTextEdit, QLineEdit, QComboBox, QSpinBox, QDateTimeEdit, QTimeEdit {
        background-color: rgb(18, 26, 61);
        color: white;
        border-radius: 5px;
        padding: 5px 8px;
        font-size: 12px;
        border: 1px solid #2c3457;
    }
    
    #disclaimerWindow {
        background-color: rgb(13, 17, 48);
        color: white;
    }
        

    /* Таблицы */
    QTableWidget {
        background-color: rgb(18, 26, 61);
        color: white;
        /* gridline-color: #415a77;*/
        font-size: 14px;
        border: none;
    }

    QTableWidget QHeaderView::section {
        background-color: #415a77;
        color: white;
        font-weight: bold;
        border: 2px solid red;
        padding: 4px;
    }

    /* Вкладки */
    QTabWidget::pane {
        border: none;
    }

    QTabBar::tab {
        background: rgb(12,17,47);
        color: white;
        font-weight: bold;
        padding-top: 8px;
        width: 120px;
        padding-left: 15px;
        padding-right: 15px;
        padding-bottom: -20px;
        border-radius: 5px;
        margin-bottom: 50px;
    }

    QTabBar::tab:selected {
        background: #121a3d;
    }
     QTabWidget::pane {
        border: none;
        }

    /* Текстовый браузер */
    QTextBrowser {
        background-color: rgb(18, 26, 61);
        color: white;
        border-radius: 5px;
        padding: 5px;
        font-size: 12px;
    }

    /* Специфичные стили */
    QComboBox::drop-down {
        image: url(":/icons/arrow.ico");
        width: 12px;
        margin-right: 8px;
    }

    QComboBox QListView {
        background-color: rgb(25, 34, 74);
        outline: 0px;
        padding: 2px;
        border-radius: 5px;
        border: none;
    }

    QComboBox QListView:item {
        padding: 5px;
        border-radius: 3px;
        border-left: 2px solid rgb(18, 26, 61);
    }

    QComboBox QListView:item:hover {
        background: rgb(26,38,85);
        border-left: 2px solid rgb(33,62,118);
    }
    
    QDateTimeEdit {
    background-color: rgb(18, 26, 61); /* Светлый фон */
    color: white; /* Тёмный текст */
    border: none;
    border-radius: 5px;
    padding: 8px;
    font-size: 12px;
}

QDateTimeEdit::hover {
    cursor: pointer;
}

QDateTimeEdit::drop-down {
    image: url(":/icons/arrow.ico"); /* Используется та же иконка */
    width: 12px;
    margin-right: 8px;
}

QCalendarWidget QToolButton#qt_calendar_prevmonth {
    qproperty-icon: url(":/icons/arrow-left.ico");
}

QCalendarWidget QToolButton#qt_calendar_nextmonth {
    qproperty-icon: url(":/icons/arrow-right.ico");
}

QCalendarWidget QToolButton {
    background-color: #0d1130;
}

QCalendarWidget QToolButton::hover {
    background-color: rgb(18, 26, 61);
}

QCalendarWidget QMenu {
    background-color: #0d1130;
}
QCalendarWidget QWidget {
    background-color: #0d1130;
}



QCalendarWidget QTableView {
    background-color: rgb(18, 26, 61); 
    alternate-background-color: rgb(13,17,48); 
}
                                            
        QSplitter::handle {
        image: url(":/icons/pill.ico");
        margin: 0 5px;

        }

        QSplitter::handle:horizontal {
        width: 18px;
        }

        QSplitter::handle:vertical {
        height: 12px;
        }

        QSplitter::handle:pressed {
        url(":/icons/pill.ico");
        }                                    
"""

light_theme = """
    /* Основные стили */
    QMainWindow {
        background-color: rgb(240, 240, 240);
        color: black;
    }
    
    QTabWidget:pane {
        background-color: rgb(240, 240, 240);
        color: black;
    }
    
    QWidget {
        color: black;
    }
    
    QDialog {
        background-color: rgb(240, 240, 240);
        color: black;
    }

    QMessageBox {
        background-color: rgb(240, 240, 240);
        color: black;
    }

    /* Текст и метки */
    QLabel {
        color: black;
    }

    /* Кнопки */
    QPushButton {
        background-color: rgb(230, 230, 230);
        color: black;
        border-radius: 5px;
        padding: 8px;
        font-size: 12px;
        border: 1px solid #cccccc;
    }

    QPushButton:hover {
        background-color: rgb(220, 220, 220);
    }

    QPushButton#startButton {
        background-color: rgb(100, 200, 100);
        color: white;
    }

    QPushButton#startButton:hover {
        background-color: rgb(90, 180, 90);
    }

    QPushButton#startButton:pressed {
        background-color: rgb(80, 160, 80);
    }

    QPushButton#stopButton {
        background-color: #ff6b6b;
        color: white;
    }

    QPushButton#stopButton:hover {
        background-color: #ff5252;
    }

    QPushButton#stopButton:pressed {
        background-color: #ff3838;
    }

    /* Поля ввода */
    QLineEdit, QComboBox, QSpinBox, QDateTimeEdit, QTimeEdit {
        background-color: white;
        color: black;
        border-radius: 5px;
        padding: 5px 8px;
        font-size: 12px;
        border: 1px solid #cccccc;
    }

    /* Таблицы */
    QTableWidget {
        background-color: white;
        color: black;
        /* gridline-color: #dddddd; */
        font-size: 14px;
        border: 0px solid #dddddd;
    }

    QTableWidget QHeaderView::section {
        background-color: #f0f0f0;
        color: black;
        font-weight: bold;
        border: 0px solid #dddddd;
        padding: 4px;
    }

    /* Вкладки */
    QTabWidget::pane {
        border: 0px solid #cccccc;
        background: white;
    }

    QTabBar::tab {
        background: #f0f0f0;
        color: black;
        font-weight: bold;
        padding-top: 8px;
        width: 120px;
        padding-left: 15px;
        padding-right: 15px;
        padding-bottom: -20px;
        border-radius: 5px;
        margin-bottom: 50px;
    }

    QTabBar::tab:selected {
        background: white;
        border-bottom: 2px solid #4a90e2;
    }
     QTabWidget::pane {
        border: none;
        }

    /* Текстовый браузер */
    QTextBrowser {
        background-color: white;
        color: black;
        border-radius: 5px;
        padding: 5px;
        font-size: 12px;
        border: 1px solid #cccccc;
    }

    /* Специфичные стили */
    QComboBox::drop-down {
        image: url(":/icons/dark/arrow.ico");
        width: 12px;
        margin-right: 8px;
    }

    QComboBox QListView {
        background-color: white;
        outline: 0px;
        padding: 2px;
        border-radius: 5px;
        border: 1px solid #cccccc;
    }

    QComboBox QListView:item {
        padding: 5px;
        border-radius: 3px;
        border-left: 2px solid #e0e0e0;
    }

    QComboBox QListView:item:hover {
        background: #e6f2ff;
        border-left: 2px solid #4a90e2;
    }
    
    QDateTimeEdit {
    background-color: rgb(245, 245, 245); /* Светлый фон */
    color: black; /* Тёмный текст */
    border: 1px solid #ccc;
    border-radius: 5px;
    padding: 8px;
    font-size: 12px;
}

QDateTimeEdit::hover {
    cursor: pointer;
}

QDateTimeEdit::drop-down {
    image: url(":/icons/dark/arrow.ico"); /* Используется та же иконка */
    width: 12px;
    margin-right: 8px;
}

QCalendarWidget QToolButton#qt_calendar_prevmonth {
    qproperty-icon: url(":/icons/dark/arrow-left.ico");
}

QCalendarWidget QToolButton#qt_calendar_nextmonth {
    qproperty-icon: url(":/icons/dark/arrow-right.ico");
}

QCalendarWidget QMenu {
    background-color: #e0e0e0;
}
QCalendarWidget QWidget {
    background-color: #e0e0e0;
}


QCalendarWidget QHeaderView {
    background-color: #e0e0e0; /* Светлый фон заголовка */
    color: black;
    font-weight: bold;
}

QCalendarWidget QTableView {
    alternate-background-color: rgb(235, 235, 235); /* Светлая альтернатива строк */
}

                                            
        QSplitter::handle {
        image: url(":/icons/dark/pill.ico");
        margin: 0 5px;

        }

        QSplitter::handle:horizontal {
        width: 18px;
        }

        QSplitter::handle:vertical {
        height: 12px;
        }

        QSplitter::handle:pressed {
        url(":/icons/pill.ico");
        }                                        
"""


def blocked_cell(theme):
    if theme == 'dark':
        return """
QLineEdit {
    background-color: #192142; border-radius: 0px; color: #8996c7;
}
"""
    else:
        return """
QLineEdit {
    background-color: #e5e5e5; border-radius: 0px; color: #8996c7;
}
"""


def allowed_cell(theme):
    if theme == 'dark':
        return """
QLineEdit {
    background-color: #121a3d;border-radius: 0px;
}
"""
    else:
        return """
QLineEdit { 
    background-color: #f4f4f4;border-radius: 0px;
}
"""


def allowed_color(theme):
    if theme == 'dark':
        return "#121a3d"
    return "#f4f4f4"


def background_color(theme):
    if theme == 'dark':
        return "#0d1130"
    return "#f0f0f0"


def transparent_text_color(theme):
    if theme == 'dark':
        return "rgba(255, 255, 255, 150)"
    return "rgba(0, 0, 0, 150)"
