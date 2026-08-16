from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.label = QLabel("Prévia da Legenda:")
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setMaximumHeight(150)
        layout.addWidget(self.label)
        layout.addWidget(self.text_preview)

    def set_text(self, text):
        self.text_preview.setPlainText(text.replace('\r', '\n'))