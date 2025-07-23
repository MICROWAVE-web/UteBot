light_theme = """
QMainWindow {
    background-color: white;
    color: black;
}
QLabel, QTableWidget, QTextBrowser, QLineEdit, QPushButton {
    color: black;
    background-color: white;
}
QHeaderView::section {
    background-color: lightgray;
    color: black;
}
"""

dark_theme = """
QMainWindow {
    background-color: rgb(12,17,47);
    color: white;
}
QLabel, QTableWidget, QTextBrowser, QLineEdit, QPushButton {
    color: white;
    background-color: rgb(18, 26, 61);
}
QHeaderView::section {
    background-color: rgb(18, 26, 61);
    color: white;
}
"""
