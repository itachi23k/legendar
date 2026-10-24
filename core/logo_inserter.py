from PySide6.QtGui import QImage, QPainter, QTransform
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

    def apply_logo_to_image(self, img: QImage) -> bool:
        """Desenha a logo diretamente em uma instância de QImage existente."""
        if not self.logo_exists() or img.isNull():
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
        return True

    def insert_logo(self, image_path, output_path, rotate_and_stretch=False, target_size=(1440, 1080)):
        """Insere a logo na imagem."""
        if not self.logo_exists():
            return False

        img = QImage(str(image_path))
        if img.isNull():
            return False

        if rotate_and_stretch:
            img = img.transformed(QTransform().rotate(-90), Qt.SmoothTransformation)
            target_w, target_h = target_size
            img = img.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        success = self.apply_logo_to_image(img)
        if not success:
            return False

        saved = img.save(str(output_path))
        
        if saved:
            try:
                ExifWriter.preserve_original_exif(image_path, output_path, reset_orientation=rotate_and_stretch)
            except:
                pass
        
        return saved

    @staticmethod
    def composite_logo_and_legend(image_path, output_path, logo_inserter, legend_renderer,
                                  text, font_name,
                                  rotate_and_stretch=False, target_size=(1440, 1080)):
        """Combina logo e legenda em uma única operação."""
        img = QImage(str(image_path))
        if img.isNull():
            return False

        if rotate_and_stretch:
            img = img.transformed(QTransform().rotate(-90), Qt.SmoothTransformation)
            target_w, target_h = target_size
            img = img.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        if logo_inserter and logo_inserter.logo_exists():
            logo_inserter.apply_logo_to_image(img)

        legend_renderer.apply_legend_to_image(img, text, font_name)

        success = img.save(str(output_path))

        if success:
            try:
                ExifWriter.preserve_original_exif(image_path, output_path, reset_orientation=rotate_and_stretch)
            except:
                pass

        return success