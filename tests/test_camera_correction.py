import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from PIL import Image
import piexif
import shutil
import tempfile

from gui.main_window import MainWindow
from gui.widgets.camera_correction_widget import CameraCorrectionWidget
from core.legend_renderer import LegendRenderer
from core.logo_inserter import LogoInserter
from core.file_processor import FileProcessor
from core.config_manager import ConfigManager
from core.exif_writer import ExifWriter

app = QApplication.instance() or QApplication(sys.argv)

class TestCameraCorrection(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = ConfigManager()

        # Create dummy logo
        self.logo_path = Path(self.temp_dir) / "logo.jpg"
        logo_img = Image.new("RGB", (200, 100), (0, 0, 255))
        logo_img.save(self.logo_path)

        # Create dummy input image (1440x1080)
        self.input_img_path = Path(self.temp_dir) / "test_photo.jpg"
        input_img = Image.new("RGB", (1440, 1080), (120, 120, 120))
        
        # Add EXIF with Orientation = 6 (Rotate 90 CW) to verify normalization
        exif_dict = {
            "0th": {piexif.ImageIFD.Orientation: 6},
            "Exif": {},
            "GPS": {},
            "1st": {},
            "thumbnail": None
        }
        exif_bytes = piexif.dump(exif_dict)
        input_img.save(self.input_img_path, exif=exif_bytes)

        self.renderer = LegendRenderer()
        self.logo_inserter = LogoInserter(str(self.logo_path))
        self.processor = FileProcessor(self.renderer, self.logo_inserter)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_renderer_rotate_and_stretch(self):
        output_path = Path(self.temp_dir) / "output_rot.jpg"
        success = self.renderer.render(
            str(self.input_img_path), str(output_path),
            text="TESTE ROTACAO\rESTACA 100",
            rotate_and_stretch=True,
            target_size=(1440, 1080)
        )
        self.assertTrue(success)
        self.assertTrue(output_path.exists())

        # Verify output dimensions
        with Image.open(output_path) as out_img:
            self.assertEqual(out_img.size, (1440, 1080))

        # Verify EXIF orientation was reset to 1
        exif_data = piexif.load(str(output_path))
        self.assertEqual(exif_data["0th"].get(piexif.ImageIFD.Orientation), 1)

    def test_logo_composite_rotate_and_stretch(self):
        output_path = Path(self.temp_dir) / "output_composite.jpg"
        success = LogoInserter.composite_logo_and_legend(
            str(self.input_img_path), str(output_path),
            self.logo_inserter, self.renderer,
            text="TESTE COM LOGO\rESTACA 200",
            font_name="Arial",
            rotate_and_stretch=True,
            target_size=(1440, 1080)
        )
        self.assertTrue(success)
        self.assertTrue(output_path.exists())

        with Image.open(output_path) as out_img:
            self.assertEqual(out_img.size, (1440, 1080))

    def test_file_processor_rotate_and_stretch(self):
        results = self.processor.process_batch(
            [str(self.input_img_path)],
            text="TESTE BATCH\rESTACA 300",
            font_name="Arial",
            output_folder=self.temp_dir,
            prefix="_IND_ROT",
            apply_logo=True,
            rotate_and_stretch=True,
            target_size=(1440, 1080)
        )
        self.assertEqual(len(results), 1)
        res_path = Path(results[0])
        self.assertTrue(res_path.exists())
        self.assertIn("_IND_ROT", res_path.name)
        with Image.open(res_path) as out_img:
            self.assertEqual(out_img.size, (1440, 1080))

    def test_camera_correction_widget_structure(self):
        widget = CameraCorrectionWidget(self.config, self.renderer, self.logo_inserter, self.processor)
        self.assertEqual(widget.sub_tabs.count(), 2)
        self.assertEqual(widget.sub_tabs.tabText(0), "Edição Individual")
        self.assertEqual(widget.sub_tabs.tabText(1), "Edição em Lote")
        self.assertTrue(widget.individual_editor.rotate_and_stretch)
        self.assertEqual(widget.individual_editor.target_size, (1440, 1080))
        self.assertTrue(widget.batch_editor.rotate_and_stretch)
        self.assertEqual(widget.batch_editor.target_size, (1440, 1080))

    def test_main_window_has_three_tabs(self):
        window = MainWindow()
        self.assertEqual(window.tab_widget.count(), 3)
        self.assertEqual(window.tab_widget.tabText(0), "Edição Individual")
        self.assertEqual(window.tab_widget.tabText(1), "Edição em Lote")
        self.assertEqual(window.tab_widget.tabText(2), "Correção de Câmera")
        self.assertIsInstance(window.tab_widget.widget(2), CameraCorrectionWidget)

if __name__ == "__main__":
    unittest.main()
