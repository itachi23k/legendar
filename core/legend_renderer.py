from PySide6.QtGui import QImage, QPainter, QFont, QColor, QFontMetrics, QTransform
from PySide6.QtCore import Qt, QPointF
from core.font_manager import FontManager
from core.exif_writer import ExifWriter

class LegendRenderer:
    """Aplica legenda (texto com sombra) em uma imagem."""

    def __init__(self, margin_x_pct=3.0, margin_y_pct=5.0,
                 text_size_pct=3.8, leading_pct=4.5, tracking=0,
                 default_font="Araboto-Normal", preserve_exif=True):
        self.margin_x_pct = margin_x_pct
        self.margin_y_pct = margin_y_pct
        self.text_size_pct = text_size_pct
        self.leading_pct = leading_pct
        self.tracking = tracking
        self.default_font = default_font
        self.preserve_exif = preserve_exif

    def apply_legend_to_image(self, img: QImage, text, font_name=None,
                              color=(255, 255, 255), shadow_color=(0, 0, 0, 128),
                              shadow_offset_factor=0.002):
        """Desenha o texto com sombra diretamente em uma instância de QImage."""
        if img.isNull():
            return False

        if font_name is None:
            font_name = self.default_font

        doc_w = img.width()
        doc_h = img.height()
        margin_x = (self.margin_x_pct / 100) * doc_w
        margin_y = (self.margin_y_pct / 100) * doc_h
        text_size = (self.text_size_pct / 100) * doc_h
        leading = (self.leading_pct / 100) * doc_h
        shadow_offset = max(3, doc_w * shadow_offset_factor)

        if font_name == "Araboto-Normal":
            font = FontManager.get_araboto_font(text_size)
        else:
            font = QFont(font_name)
            font.setPixelSize(int(text_size))
            font.setHintingPreference(QFont.PreferFullHinting)
            font.setStyleStrategy(QFont.PreferAntialias)

        tracking_spacing = (self.tracking / 1000) * text_size
        font.setLetterSpacing(QFont.AbsoluteSpacing, tracking_spacing)

        lines = text.split('\r')
        line_count = len(lines)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setFont(font)

        metrics = QFontMetrics(font)
        baseline_last_line = doc_h - margin_y

        for i, line in enumerate(lines):
            baseline_y = baseline_last_line - (line_count - 1 - i) * leading
            text_width = metrics.horizontalAdvance(line)
            x_text = doc_w - margin_x - text_width

            shadow_pen = QColor(*shadow_color)
            painter.setPen(shadow_pen)
            painter.drawText(QPointF(x_text + shadow_offset, baseline_y + shadow_offset), line)

            white_pen = QColor(*color)
            painter.setPen(white_pen)
            painter.drawText(QPointF(x_text, baseline_y), line)

        painter.end()
        return True

    def render(self, image_path, output_path, text, font_name=None,
               color=(255, 255, 255), shadow_color=(0, 0, 0, 128),
               shadow_offset_factor=0.002,
               rotate_and_stretch=False, target_size=(1440, 1080)):
        """Carrega a imagem, desenha o texto e salva."""
        img = QImage(str(image_path))
        if img.isNull():
            return False

        if rotate_and_stretch:
            # 1. Girar 90 graus à esquerda (anti-horário = -90 graus)
            img = img.transformed(QTransform().rotate(-90), Qt.SmoothTransformation)
            # 2. Esticar para target_size (ex: 1440x1080)
            target_w, target_h = target_size
            img = img.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        self.apply_legend_to_image(img, text, font_name, color, shadow_color, shadow_offset_factor)
        
        success = img.save(str(output_path))
        
        if success and self.preserve_exif:
            try:
                ExifWriter.preserve_original_exif(image_path, output_path, reset_orientation=rotate_and_stretch)
            except:
                pass
        
        return success