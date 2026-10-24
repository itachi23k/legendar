import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate

from gui.dialogs.date_rules_dialog import DateRuleWidget, DateRulesDialog
from gui.widgets.batch_editor_widget import BatchProcessorThread, BatchEditorWidget
from core.metadata_parser import MetadataParser
from core.legend_renderer import LegendRenderer
from core.logo_inserter import LogoInserter
from core.config_manager import ConfigManager
from PIL import Image
import piexif
import shutil
import tempfile

app = QApplication.instance() or QApplication(sys.argv)

class TestDateRules(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 1. Tests for DateRuleWidget & DateRulesDialog
    # -------------------------------------------------------------
    def test_date_rule_widget_default(self):
        today_str = QDate.currentDate().toString("dd/MM/yyyy")
        widget = DateRuleWidget()
        rule = widget.get_rule()
        self.assertEqual(rule['original'], today_str)
        self.assertEqual(rule['action'], 'alterar')
        self.assertEqual(rule['new'], today_str)
        self.assertFalse(widget.new_date_edit.isHidden())

    def test_date_rule_widget_omitir(self):
        orig_date = QDate(2025, 5, 10)
        widget = DateRuleWidget(original_date=orig_date, action="omitir")
        rule = widget.get_rule()
        self.assertEqual(rule['original'], "10/05/2025")
        self.assertEqual(rule['action'], "omitir")
        self.assertTrue(widget.new_date_edit.isHidden())

    def test_date_rule_widget_toggle_action(self):
        orig_date = QDate(2025, 5, 10)
        nova_date = QDate(2025, 6, 15)
        widget = DateRuleWidget(original_date=orig_date, action="alterar", new_date=nova_date)
        self.assertEqual(widget.get_rule()['action'], 'alterar')
        self.assertFalse(widget.new_date_edit.isHidden())

        # Change to omit
        widget.combo_action.setCurrentIndex(1) # "Omitir data"
        self.assertEqual(widget.get_rule()['action'], 'omitir')
        self.assertTrue(widget.new_date_edit.isHidden())

        # Change back to alterar
        widget.combo_action.setCurrentIndex(0) # "Alterar para"
        self.assertEqual(widget.get_rule()['action'], 'alterar')
        self.assertFalse(widget.new_date_edit.isHidden())

    def test_date_rules_dialog_load_and_save(self):
        initial_rules = [
            {"original": "01/01/2025", "action": "alterar", "new": "02/01/2025"},
            {"original": "15/02/2025", "action": "omitir", "new": "15/02/2025"}
        ]
        dialog = DateRulesDialog(initial_rules=initial_rules, ignore_non_matching=True)
        settings = dialog.get_settings()

        self.assertTrue(settings['ignore_non_matching'])
        self.assertEqual(len(settings['date_rules']), 2)
        self.assertEqual(settings['date_rules'][0], {
            "original": "01/01/2025", "action": "alterar", "new": "02/01/2025"
        })
        self.assertEqual(settings['date_rules'][1], {
            "original": "15/02/2025", "action": "omitir", "new": "15/02/2025"
        })

    def test_date_rules_dialog_add_remove(self):
        dialog = DateRulesDialog(initial_rules=[], ignore_non_matching=False)
        self.assertFalse(dialog.check_ignore.isChecked())
        self.assertEqual(len(dialog.rules_widgets), 0)

        # Add rule
        dialog._on_add_rule()
        self.assertEqual(len(dialog.rules_widgets), 1)

        # Remove rule
        widget = dialog.rules_widgets[0]
        dialog._on_remove_rule(widget)
        self.assertEqual(len(dialog.rules_widgets), 0)

    # -------------------------------------------------------------
    # 2. Tests for BatchProcessorThread date rule logic
    # -------------------------------------------------------------
    def test_apply_date_rules_alterar(self):
        settings = {
            'date_rules': [
                {"original": "10/05/2024", "action": "alterar", "new": "20/05/2024"}
            ],
            'ignore_non_matching': True
        }
        thread = BatchProcessorThread([], settings, None, None)
        meta = {'data': '10/05/2024', 'obra': 'TEST', 'servico': 'SERV', 'estaca': '10', 'lado': 'D', 'utm': '20M'}

        result = thread._apply_date_rules(dict(meta))
        self.assertIsNotNone(result)
        self.assertEqual(result['data'], '20/05/2024')
        self.assertFalse(result.get('omit_date', True))

    def test_apply_date_rules_omitir(self):
        settings = {
            'date_rules': [
                {"original": "10/05/2024", "action": "omitir", "new": "10/05/2024"}
            ],
            'ignore_non_matching': True
        }
        thread = BatchProcessorThread([], settings, None, None)
        meta = {'data': '10/05/2024', 'obra': 'TEST', 'servico': 'SERV', 'estaca': '10', 'lado': 'D', 'utm': '20M'}

        result = thread._apply_date_rules(dict(meta))
        self.assertIsNotNone(result)
        self.assertEqual(result['data'], '')
        self.assertTrue(result.get('omit_date', False))

    def test_apply_date_rules_non_matching_ignored(self):
        settings = {
            'date_rules': [
                {"original": "10/05/2024", "action": "alterar", "new": "20/05/2024"}
            ],
            'ignore_non_matching': True
        }
        thread = BatchProcessorThread([], settings, None, None)
        meta = {'data': '11/05/2024', 'obra': 'TEST'}

        result = thread._apply_date_rules(dict(meta))
        self.assertIsNone(result)

    def test_apply_date_rules_non_matching_not_ignored(self):
        settings = {
            'date_rules': [
                {"original": "10/05/2024", "action": "alterar", "new": "20/05/2024"}
            ],
            'ignore_non_matching': False
        }
        thread = BatchProcessorThread([], settings, None, None)
        meta = {'data': '11/05/2024', 'obra': 'TEST'}

        result = thread._apply_date_rules(dict(meta))
        self.assertIsNotNone(result)
        self.assertEqual(result['data'], '11/05/2024')

    def test_apply_date_rules_empty_date(self):
        settings = {
            'date_rules': [{"original": "10/05/2024", "action": "alterar", "new": "20/05/2024"}],
            'ignore_non_matching': True
        }
        thread = BatchProcessorThread([], settings, None, None)
        meta = {'data': '', 'obra': 'TEST'}

        # Ignored when ignore_non_matching is True
        result = thread._apply_date_rules(dict(meta))
        self.assertIsNone(result)

        # Retained when ignore_non_matching is False
        settings['ignore_non_matching'] = False
        thread = BatchProcessorThread([], settings, None, None)
        result = thread._apply_date_rules(dict(meta))
        self.assertIsNotNone(result)
        self.assertEqual(result['data'], '')

    # -------------------------------------------------------------
    # 3. Legend building with date rules
    # -------------------------------------------------------------
    def test_build_legend_text_with_date(self):
        settings = {'show_date': True}
        thread = BatchProcessorThread([], settings, None, None)
        data = {
            'utm': '20M 123456 7890123',
            'obra': 'TT-563/2024',
            'estaca': '10+00,00',
            'lado': 'D',
            'servico': 'ROÇADA',
            'data': '24/08/2026',
            'omit_date': False
        }
        legend = thread._build_legend_text(data)
        lines = legend.split('\r')
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[6], '24/08/2026')

    def test_build_legend_text_omit_date(self):
        settings = {'show_date': True}
        thread = BatchProcessorThread([], settings, None, None)
        data = {
            'utm': '20M 123456 7890123',
            'obra': 'TT-563/2024',
            'estaca': '10+00,00',
            'lado': 'D',
            'servico': 'ROÇADA',
            'data': '',
            'omit_date': True
        }
        legend = thread._build_legend_text(data)
        lines = legend.split('\r')
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[6], ' ')

    # -------------------------------------------------------------
    # 4. Output path generation
    # -------------------------------------------------------------
    def test_output_path_date_rules(self):
        settings = {
            'use_date_rules': True,
            'show_date': True,
            'output_folder': ''
        }
        thread = BatchProcessorThread([], settings, None, None)
        
        # When date is shown
        p1 = thread._get_output_path("C:/photos/image_01.jpg", {'omit_date': False})
        self.assertTrue(p1.endswith("image_01_REG.jpg"))

        # When date is omitted via rule
        p2 = thread._get_output_path("C:/photos/image_01.jpg", {'omit_date': True})
        self.assertTrue(p2.endswith("image_01_REG_SD.jpg"))

    # -------------------------------------------------------------
    # 5. BatchEditorWidget rules summary & preferences test
    # -------------------------------------------------------------
    def test_batch_editor_widget_summary_and_prefs(self):
        config_path = Path(self.temp_dir) / "config.json"
        config = ConfigManager(str(config_path))
        renderer = LegendRenderer()
        logo_inserter = LogoInserter("non_existent_logo.png")
        
        widget = BatchEditorWidget(config, renderer, logo_inserter, None)
        widget.date_rules = [
            {"original": "01/05/2024", "action": "alterar", "new": "10/05/2024"},
            {"original": "02/05/2024", "action": "omitir", "new": "02/05/2024"}
        ]
        widget._update_rules_summary()
        self.assertIn("2 regra(s)", widget.lbl_rules.text())
        self.assertIn("1 alteração(ões)", widget.lbl_rules.text())
        self.assertIn("1 omissão(ões)", widget.lbl_rules.text())

    # -------------------------------------------------------------
    # 6. End-to-end batch processing test
    # -------------------------------------------------------------
    def test_end_to_end_batch_processing(self):
        img_dir = Path(self.temp_dir) / "images"
        out_dir = Path(self.temp_dir) / "output"
        img_dir.mkdir()
        out_dir.mkdir()

        test_files = []
        dates = ["01/05/2024", "02/05/2024", "03/05/2024"]

        for i, dt in enumerate(dates):
            img_path = img_dir / f"test_{i+1}_CLEAN.jpg"
            img = Image.new('RGB', (400, 300), color=(100, 150, 200))
            
            # Add user comment
            comment = f"TT-563/2024|ROÇADA|{i*10}+00,00|D|20M 100 200|{dt}|10:00:00"
            comment_bytes = b'UNICODE\x00' + comment.encode('utf-16')
            exif_dict = {"0th": {}, "Exif": {piexif.ExifIFD.UserComment: comment_bytes}, "GPS": {}, "1st": {}, "thumbnail": None}
            exif_bytes = piexif.dump(exif_dict)
            img.save(str(img_path), "jpeg", exif=exif_bytes)
            test_files.append(str(img_path))

        renderer = LegendRenderer()
        logo_inserter = LogoInserter("non_existent_logo.png")

        settings = {
            'use_date_rules': True,
            'date_rules': [
                {"original": "01/05/2024", "action": "alterar", "new": "10/05/2024"},
                {"original": "02/05/2024", "action": "omitir", "new": "02/05/2024"}
            ],
            'ignore_non_matching': True,
            'show_date': True,
            'output_folder': str(out_dir),
            'apply_logo': False
        }

        processor = BatchProcessorThread(test_files, settings, renderer, logo_inserter)
        processor.run()

        self.assertEqual(processor.ignored_count, 1)

        out_files = list(out_dir.glob("*.jpg"))
        self.assertEqual(len(out_files), 2)

        f1_candidates = [f for f in out_files if "test_1_CLEAN_REG.jpg" in f.name]
        self.assertEqual(len(f1_candidates), 1)
        meta1 = MetadataParser.extract_custom_metadata(f1_candidates[0])
        self.assertIsNotNone(meta1)
        self.assertEqual(meta1['data'], '10/05/2024')

        f2_candidates = [f for f in out_files if "test_2_CLEAN_REG_SD.jpg" in f.name]
        self.assertEqual(len(f2_candidates), 1)
        meta2 = MetadataParser.extract_custom_metadata(f2_candidates[0])
        self.assertIsNotNone(meta2)
        self.assertEqual(meta2['data'], '')

if __name__ == '__main__':
    unittest.main()
