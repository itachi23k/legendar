from PySide6.QtWidgets import QListWidget, QAbstractItemView

class ImageListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def add_files(self, files):
        for f in files:
            self.addItem(f)

    def get_files(self):
        return [self.item(i).text() for i in range(self.count())]

    def clear(self):
        super().clear()