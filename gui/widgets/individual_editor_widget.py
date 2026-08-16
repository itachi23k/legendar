from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QFileDialog, QMessageBox, QCheckBox, QLabel)
from gui.widgets.image_list_widget import ImageListWidget
from gui.widgets.legend_settings_widget import LegendSettingsWidget
from gui.widgets.preview_widget import PreviewWidget
from core.metadata_parser import MetadataParser

class IndividualEditorWidget(QWidget):
    """Aba para edição individual de imagens."""

    def __init__(self, config, renderer, logo_inserter, processor):
        super().__init__()
        self.config = config
        self.renderer = renderer
        self.logo_inserter = logo_inserter
        self.processor = processor

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        main_layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Imagens Selecionadas:"))
        self.image_list = ImageListWidget()
        self.btn_add_images = QPushButton("Adicionar Imagens...")
        self.btn_clear_images = QPushButton("Limpar Lista")
        left_panel.addWidget(self.image_list)
        left_panel.addWidget(self.btn_add_images)
        left_panel.addWidget(self.btn_clear_images)

        self.settings = LegendSettingsWidget(self.config)

        main_layout.addLayout(left_panel, 2)
        main_layout.addWidget(self.settings, 3)
        layout.addLayout(main_layout)

        self.check_apply_logo = QCheckBox("Inserir logo no canto superior direito")
        self.check_apply_logo.setChecked(True)
        layout.addWidget(self.check_apply_logo)

        self.preview = PreviewWidget()
        layout.addWidget(self.preview)

        self.btn_generate = QPushButton("Gerar Legendas nas Imagens Selecionadas")
        self.btn_generate.setMinimumHeight(40)
        layout.addWidget(self.btn_generate)

    def _connect_signals(self):
        self.btn_add_images.clicked.connect(self._on_add_images)
        self.btn_clear_images.clicked.connect(self.image_list.clear)
        self.btn_generate.clicked.connect(self._on_generate)
        self.settings.data_changed.connect(self._update_preview)
        self.settings.ler_foto_requested.connect(self._on_ler_foto)

    def _on_add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar Imagens", "",
            "Imagens (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)"
        )
        if files:
            self.image_list.add_files(files)

    def _update_preview(self):
        text = self.settings.build_legend_text()
        self.preview.set_text(text)

    def _on_ler_foto(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Aviso", "Selecione uma imagem na lista para ler os metadados.")
            return

        image_path = selected_items[0].text()
        meta = MetadataParser.extract_custom_metadata(image_path)

        if meta:
            if 'servico' in meta:
                meta['servico'] = MetadataParser.limpar_texto(meta['servico'])
            if 'obra' in meta:
                meta['obra'] = MetadataParser.limpar_texto(meta['obra'])
            if 'lado' in meta:
                meta['lado'] = MetadataParser.limpar_texto(meta['lado'])
            
            self.settings.fill_from_metadata(meta)
        else:
            QMessageBox.information(self, "Sem metadados", "Não foi possível extrair metadados desta imagem.")

    def _on_generate(self):
        images = self.image_list.get_files()
        if not images:
            QMessageBox.warning(self, "Aviso", "Nenhuma imagem selecionada.")
            return

        text = self.settings.build_legend_text()
        font = self.settings.get_selected_font()
        apply_logo = self.check_apply_logo.isChecked()

        try:
            results = self.processor.process_batch(
                images, text, font,
                apply_logo=apply_logo
            )
            QMessageBox.information(self, "Sucesso", f"{len(results)} imagens processadas.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))