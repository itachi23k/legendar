from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Qt
from pathlib import Path
from core.exif_writer import ExifWriter

class LogoInserter:
    """Insere uma logo no canto superior direito da imagem."""

    def __init__(self, logo_path, logo_width_pct=20.0, margin_x_pct=2.8, margin_y_pct=3.7):
        self.logo_path = Path(logo_path)
        self.logo_width_pct = logo_width_pct
        self.margin_x_pct = margin_x_pct
        self.margin_y_pct = margin_y_pct
        self.logo_image = QImage(str(self.logo_path)) if self.logo_path.exists() else None

    def logo_exists(self):
        return self.logo_image is not None and not self.logo_image.isNull()

    def insert_logo(self, image_path, output_path):
        """Insere a logo na imagem."""
        if not self.logo_exists():
            return False

        img = QImage(image_path)
        if img.isNull():
            return False

        doc_w = img.width()
        doc_h = img.height()

        logo_target_width = (self.logo_width_pct / 100) * doc_w
        original_logo_width = self.logo_image.width()
        original_logo_height = self.logo_image.height()

        if original_logo_width <= 0 or original_logo_height <= 0:
            return False

        scale_factor = logo_target_width / original_logo_width
        logo_target_height = original_logo_height * scale_factor

        scaled_logo = self.logo_image.scaled(
            int(logo_target_width),
            int(logo_target_height),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        margin_x = (self.margin_x_pct / 100) * doc_w
        margin_y = (self.margin_y_pct / 100) * doc_h

        x_pos = int(doc_w - scaled_logo.width() - margin_x)
        y_pos = int(margin_y)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(x_pos, y_pos, scaled_logo)
        painter.end()

        success = img.save(output_path)
        
        if success:
            try:
                ExifWriter.preserve_original_exif(image_path, output_path)
            except:
                pass
        
        return success

    @staticmethod
    def composite_logo_and_legend(image_path, output_path, logo_inserter, legend_renderer, text, font_name):
        """Combina logo e legenda em uma única operação."""
        temp_path = output_path + ".temp.png"
        
        if logo_inserter.logo_exists():
            if not logo_inserter.insert_logo(image_path, temp_path):
                temp_path = image_path
        else:
            temp_path = image_path

        success = legend_renderer.render(temp_path, output_path, text, font_name)

        if temp_path != image_path and Path(temp_path).exists():
            Path(temp_path).unlink()

        if success:
            try:
                ExifWriter.preserve_original_exif(image_path, output_path)
            except:
                pass

        return success