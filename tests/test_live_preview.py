import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPixmap
from PIL import Image
import shutil
import tempfile

from gui.widgets.preview_widget import PreviewWidget, ImageCanvasWidget
from gui.widgets.individual_editor_widget import IndividualEditorWidget
from core.config_manager import ConfigManager
from core.legend_renderer import LegendRenderer
from core.logo_inserter import LogoInserter
from core.file_processor import FileProcessor

app = QApplication.instance() or QApplication(sys.argv)

class TestLivePreview(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = ConfigManager()

        # Create dummy logo
        self.logo_path = Path(self.temp_dir) / "logo.jpg"
        logo_img = Image.new("RGB", (200, 100), (0, 0, 255))
        logo_img.save(self.logo_path)

        # Create dummy photo (1440x1080)
        self.img_path = Path(self.temp_dir) / "sample_photo.jpg"
        sample_img = Image.new("RGB", (1440, 1080), (100, 150, 200))
        sample_img.save(self.img_path)

        self.renderer = LegendRenderer()
        self.logo_inserter = LogoInserter(str(self.logo_path))
        self.processor = FileProcessor(self.renderer, self.logo_inserter)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preview_widget_structure(self):
        preview = PreviewWidget()
        self.assertIsInstance(preview.canvas, ImageCanvasWidget)
        self.assertIsNotNone(preview.text_preview)
        
        # Test setting and clearing image
        test_img = QImage(100, 100, QImage.Format_RGB32)
        preview.set_image(test_img, "teste.jpg (100x100)")
        self.assertIsNotNone(preview.canvas.current_pixmap)
        self.assertEqual(preview.lbl_info.text(), "teste.jpg (100x100)")

        preview.clear_image()
        self.assertIsNone(preview.canvas.current_pixmap)
        self.assertEqual(preview.lbl_info.text(), "")

    def test_individual_editor_live_preview_selection(self):
        widget = IndividualEditorWidget(
            self.config, self.renderer, self.logo_inserter, self.processor,
            rotate_and_stretch=False
        )
        # Add files to image list
        widget.image_list.add_files([str(self.img_path)])
        widget.image_list.setCurrentRow(0)

        # Base image should be loaded
        self.assertIsNotNone(widget.base_image)
        self.assertEqual(widget.base_image.width(), 1440)
        self.assertEqual(widget.base_image.height(), 1080)

        # Preview canvas should have rendered pixmap
        self.assertIsNotNone(widget.preview.canvas.current_pixmap)
        self.assertEqual(widget.preview.canvas.current_pixmap.width(), 1440)
        self.assertEqual(widget.preview.canvas.current_pixmap.height(), 1080)
        self.assertIn("sample_photo.jpg", widget.preview.lbl_info.text())

    def test_individual_editor_camera_correction_live_preview(self):
        widget = IndividualEditorWidget(
            self.config, self.renderer, self.logo_inserter, self.processor,
            rotate_and_stretch=True, target_size=(1440, 1080)
        )
        widget.image_list.add_files([str(self.img_path)])
        widget.image_list.setCurrentRow(0)

        # Base image should be rotated and stretched back to 1440x1080
        self.assertIsNotNone(widget.base_image)
        self.assertEqual(widget.base_image.width(), 1440)
        self.assertEqual(widget.base_image.height(), 1080)

        # Preview pixmap should also be 1440x1080
        self.assertIsNotNone(widget.preview.canvas.current_pixmap)
        self.assertEqual(widget.preview.canvas.current_pixmap.width(), 1440)
        self.assertEqual(widget.preview.canvas.current_pixmap.height(), 1080)

    def test_clear_images_resets_preview(self):
        widget = IndividualEditorWidget(
            self.config, self.renderer, self.logo_inserter, self.processor
        )
        widget.image_list.add_files([str(self.img_path)])
        widget.image_list.setCurrentRow(0)
        self.assertIsNotNone(widget.preview.canvas.current_pixmap)

        widget._on_clear_images()
        self.assertIsNone(widget.preview.canvas.current_pixmap)
        self.assertIsNone(widget.base_image)

if __name__ == "__main__":
    unittest.main()
