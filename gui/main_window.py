from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from gui.widgets.individual_editor_widget import IndividualEditorWidget
from gui.widgets.batch_editor_widget import BatchEditorWidget
from core.config_manager import ConfigManager
from core.file_processor import FileProcessor
from core.legend_renderer import LegendRenderer
from core.logo_inserter import LogoInserter
from core.font_manager import FontManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerador de Legendas LCM")
        self.resize(1000, 750)

        self.config = ConfigManager()

        self.renderer = LegendRenderer(
            margin_x_pct=3.0,
            margin_y_pct=5.0,
            text_size_pct=3.8,
            leading_pct=4.5,
            tracking=0,
            default_font="Araboto-Normal"
        )

        logo_path = "G:\\Meu Drive\\LEGENDA\\logo-lcm.jpeg"
        self.logo_inserter = LogoInserter(
            logo_path=logo_path,
            logo_width_pct=20.0,
            margin_x_pct=2.8,
            margin_y_pct=3.7
        )

        self.processor = FileProcessor(self.renderer, self.logo_inserter)

        self.tab_widget = QTabWidget()
        self.individual_editor = IndividualEditorWidget(
            self.config, self.renderer, self.logo_inserter, self.processor
        )
        self.batch_editor = BatchEditorWidget(
            self.config, self.renderer, self.logo_inserter, self.processor
        )

        self.tab_widget.addTab(self.individual_editor, "Edição Individual")
        self.tab_widget.addTab(self.batch_editor, "Edição em Lote")

        self.setCentralWidget(self.tab_widget)
        self.statusBar().showMessage("Pronto")

        self._verify_resources()

    def _verify_resources(self):
        font_family = FontManager.load_araboto_font()
        if font_family:
            self.statusBar().showMessage(f"Fonte carregada: {font_family}")
        else:
            QMessageBox.warning(self, "Aviso",
                "Fonte Araboto-Normal não encontrada.\n"
                "Usando Arial como fallback.")

        if not self.logo_inserter.logo_exists():
            QMessageBox.warning(self, "Aviso",
                f"Logo não encontrada no caminho:\n{self.logo_inserter.logo_path}\n\n"
                "A opção de logo estará desativada.")