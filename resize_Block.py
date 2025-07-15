from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class ResizableBlock(QWidget):
    def __init__(self):
        super().__init__()

        # self.setStyleSheet("background-color: lightblue; border: 1px solid black;")
        self.setMinimumWidth(100)  # минимальная ширина блока


        self.resize_margin = 10  # зона захвата слева
        self.resizing = False
        self.start_mouse_pos = None
        self.start_width = None
        self.start_pos_x = None

        self.SUPERMAXWIDTH = 650

        #layout = QVBoxLayout(self)
        #label = QLabel("Содержимое блока")
        #layout.addWidget(label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_in_left_resize_area(event.pos()):
                self.resizing = True
                self.start_mouse_pos = event.globalPos()
                self.start_width = self.width()
                self.start_pos_x = self.x()

    def mouseMoveEvent(self, event):
        if self.resizing:
            delta = event.globalPos() - self.start_mouse_pos
            new_width = self.start_width - delta.x()
            new_x = self.start_pos_x + delta.x()

            # ограничим минимальную ширину
            min_width = self.minimumWidth()
            if new_width < min_width:
                new_width = min_width
                new_x = self.start_pos_x + (self.start_width - min_width)

            self.resize(new_width, self.height())
            self.setMinimumWidth(new_width)
            self.setMaximumWidth(new_width)
            self.move(new_x, self.y())
        else:
            if self.is_in_left_resize_area(event.pos()):
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.resizing = False

    def is_in_left_resize_area(self, pos):
        print(pos.x())
        return 0 <= pos.x() <= self.resize_margin
