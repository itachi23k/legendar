from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from gui.widgets.individual_editor_widget import IndividualEditorWidget
from gui.widgets.batch_editor_widget import BatchEditorWidget

class CameraCorrectionWidget(QWidget):
    """Aba para correção de fotos com bug de câmera (giro 90° à esquerda e esticamento para 1440x1080)."""

    def __init__(self, config, renderer, logo_inserter, processor, target_size=(1440, 1080)):
        super().__init__()
        self.config = config
        self.renderer = renderer
        self.logo_inserter = logo_inserter
        self.processor = processor
        self.target_size = target_size

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.sub_tabs = QTabWidget()

        self.individual_editor = IndividualEditorWidget(
            self.config, self.renderer, self.logo_inserter, self.processor,
            rotate_and_stretch=True, target_size=self.target_size
        )
        self.batch_editor = BatchEditorWidget(
            self.config, self.renderer, self.logo_inserter, self.processor,
            rotate_and_stretch=True, target_size=self.target_size
        )

        self.sub_tabs.addTab(self.individual_editor, "Edição Individual")
        self.sub_tabs.addTab(self.batch_editor, "Edição em Lote")

        layout.addWidget(self.sub_tabs)
