import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PIL import Image
import piexif
import shutil
import tempfile

from gui.widgets.individual_editor_widget import IndividualEditorWidget
from gui.widgets.camera_correction_widget import CameraCorrectionWidget
from core.config_manager import ConfigManager
from core.legend_renderer import LegendRenderer
from core.logo_inserter import LogoInserter
from core.file_processor import FileProcessor

app = QApplication.instance() or QApplication(sys.argv)

def create_image_with_metadata(path, width, height, user_comment):
    img = Image.new("RGB", (width, height), (150, 150, 150))
    # Encode UserComment with ASCII prefix as per EXIF standard
    uc_bytes = b"ASCII\x00\x00\x00" + user_comment.encode("latin-1")
    exif_dict = {
        "0th": {},
        "Exif": {piexif.ExifIFD.UserComment: uc_bytes},
        "GPS": {},
        "1st": {},
        "thumbnail": None
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, exif=exif_bytes)

def create_plain_image(path, width, height):
    img = Image.new("RGB", (width, height), (100, 100, 100))
    img.save(path)

class TestIndividualMetadataSync(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = ConfigManager()

        self.logo_path = Path(self.temp_dir) / "logo.jpg"
        create_plain_image(self.logo_path, 200, 100)

        # Foto 1: Metadados da Estaca 100, ROÇADA, Obra TT-563/2024
        self.photo1 = Path(self.temp_dir) / "photo1.jpg"
        create_image_with_metadata(
            self.photo1, 1440, 1080,
            "TT-563/2024|ROÇADA|100+0|D|20M 111111 2222222|10/05/2024|08:30:00"
        )

        # Foto 2: Metadados da Estaca 250, TAPA BURACO, Obra SR-592/2020
        self.photo2 = Path(self.temp_dir) / "photo2.jpg"
        create_image_with_metadata(
            self.photo2, 1440, 1080,
            "SR-592/2020|TAPA BURACO|250+10|E|20M 333333 4444444|15/06/2024|09:45:00"
        )

        # Foto 3: Sem metadados
        self.photo3 = Path(self.temp_dir) / "photo3.jpg"
        create_plain_image(self.photo3, 1440, 1080)

        self.renderer = LegendRenderer()
        self.logo_inserter = LogoInserter(str(self.logo_path))
        self.processor = FileProcessor(self.renderer, self.logo_inserter)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_auto_metadata_update_on_selection_change_camera_correction(self):
        """Valida que no modo de correção de câmera (IndividualEditorWidget com rotate_and_stretch=True)
        ao trocar a seleção na lista, os campos são automaticamente atualizados e não há vazamento
        de dados entre fotos abaixo e acima."""
        camera_widget = CameraCorrectionWidget(
            self.config, self.renderer, self.logo_inserter, self.processor
        )
        editor = camera_widget.individual_editor

        # Adiciona fotos na lista
        editor.image_list.add_files([str(self.photo1), str(self.photo2), str(self.photo3)])

        # 1. Seleciona a Foto 1
        editor.image_list.setCurrentRow(0)
        self.assertEqual(editor.current_image_path, str(self.photo1))
        self.assertEqual(editor.settings.combo_obra.currentText(), "TT-563/2024")
        self.assertEqual(editor.settings.combo_servico.currentText(), "ROÇADA")
        self.assertEqual(editor.settings.edit_estaca.text(), "100+0")
        self.assertEqual(editor.settings.combo_lado.currentText(), "D")
        self.assertEqual(editor.settings.edit_utm.text(), "20M 111111 2222222")
        self.assertEqual(editor.settings.edit_dia.text(), "10")
        self.assertEqual(editor.settings.combo_mes.currentText(), "05")
        self.assertEqual(editor.settings.edit_ano.text(), "2024")

        # 2. Troca para a Foto 2 (foto abaixo)
        editor.image_list.setCurrentRow(1)
        self.assertEqual(editor.current_image_path, str(self.photo2))
        self.assertEqual(editor.settings.combo_obra.currentText(), "SR-592/2020")
        self.assertEqual(editor.settings.combo_servico.currentText(), "TAPA BURACO")
        self.assertEqual(editor.settings.edit_estaca.text(), "250+10")
        self.assertEqual(editor.settings.combo_lado.currentText(), "E")
        self.assertEqual(editor.settings.edit_utm.text(), "20M 333333 4444444")
        self.assertEqual(editor.settings.edit_dia.text(), "15")
        self.assertEqual(editor.settings.combo_mes.currentText(), "06")
        self.assertEqual(editor.settings.edit_ano.text(), "2024")

        # 3. Adiciona observação na Foto 2 e troca para a Foto 3 (sem metadados)
        editor.settings.edit_obs.setPlainText("Servico realizado no periodo matutino")
        editor.image_list.setCurrentRow(2)
        self.assertEqual(editor.current_image_path, str(self.photo3))
        # Foto 3 não deve herdar dados da Foto 2 (abaixo)
        self.assertEqual(editor.settings.edit_estaca.text(), "")
        self.assertEqual(editor.settings.edit_utm.text(), "")
        self.assertEqual(editor.settings.edit_obs.toPlainText(), "")

        # 4. Volta para a Foto 2 (acima)
        editor.image_list.setCurrentRow(1)
        self.assertEqual(editor.current_image_path, str(self.photo2))
        self.assertEqual(editor.settings.edit_estaca.text(), "250+10")
        self.assertEqual(editor.settings.combo_servico.currentText(), "TAPA BURACO")
        self.assertEqual(editor.settings.edit_obs.toPlainText(), "Servico realizado no periodo matutino")

        # 5. Volta para a Foto 1 (acima da Foto 2)
        editor.image_list.setCurrentRow(0)
        self.assertEqual(editor.current_image_path, str(self.photo1))
        self.assertEqual(editor.settings.edit_estaca.text(), "100+0")
        self.assertEqual(editor.settings.combo_servico.currentText(), "ROÇADA")
        self.assertEqual(editor.settings.edit_obs.toPlainText(), "")  # Foto 1 não recebeu obs da Foto 2!

if __name__ == "__main__":
    unittest.main()
