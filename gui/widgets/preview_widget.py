from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTextEdit, QSizePolicy, QFrame)
from PySide6.QtGui import QPainter, QColor, QPixmap, QImage, QFont
from PySide6.QtCore import Qt

class ImageCanvasWidget(QWidget):
    """Área para desenhar a imagem mantendo a proporção de aspecto."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pixmap = None
        self.placeholder_text = "Selecione uma imagem na lista para visualizar a prévia ao vivo"
        self.setMinimumSize(280, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_pixmap(self, pixmap: QPixmap):
        self.current_pixmap = pixmap
        self.update()

    def clear(self):
        self.current_pixmap = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Fundo escuro elegante para destacar a foto
        painter.fillRect(self.rect(), QColor("#1c1c1e"))

        if self.current_pixmap and not self.current_pixmap.isNull():
            target_size = self.size()
            scaled = self.current_pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(QColor("#777777"))
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, self.placeholder_text)


class PreviewWidget(QWidget):
    """Widget de visualização com preview ao vivo da imagem e texto da legenda."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        self.label = QLabel("Prévia ao Vivo:")
        self.label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(self.label)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_info)
        layout.addLayout(header_layout)

        # Canvas gráfico da imagem com proporção preservada
        self.canvas = ImageCanvasWidget()
        layout.addWidget(self.canvas, 1)

        # Texto da legenda
        lbl_text = QLabel("Texto Formatado da Legenda:")
        lbl_text.setStyleSheet("font-size: 11px; font-weight: bold; color: #444;")
        layout.addWidget(lbl_text)

        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setMaximumHeight(125)
        layout.addWidget(self.text_preview)

    def set_image(self, pixmap_or_image, info: str = ""):
        if isinstance(pixmap_or_image, QImage):
            pixmap = QPixmap.fromImage(pixmap_or_image)
        elif isinstance(pixmap_or_image, QPixmap):
            pixmap = pixmap_or_image
        else:
            pixmap = None

        self.canvas.set_pixmap(pixmap)
        self.lbl_info.setText(info)

    def clear_image(self):
        self.canvas.clear()
        self.lbl_info.setText("")

    def set_text(self, text):
        self.text_preview.setPlainText(text.replace('\r', '\n'))