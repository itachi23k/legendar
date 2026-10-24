from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QFileDialog, QMessageBox, QCheckBox, QLabel, QComboBox,
                               QSplitter, QGroupBox, QScrollArea, QFrame)
from PySide6.QtGui import QTransform, QImage
from PySide6.QtCore import Qt
from gui.widgets.image_list_widget import ImageListWidget
from gui.widgets.legend_settings_widget import LegendSettingsWidget
from gui.widgets.preview_widget import PreviewWidget
from core.metadata_parser import MetadataParser

class IndividualEditorWidget(QWidget):
    """Aba para edição individual de imagens com prévia ao vivo."""

    def __init__(self, config, renderer, logo_inserter, processor,
                 rotate_and_stretch=False, target_size=(1440, 1080)):
        super().__init__()
        self.config = config
        self.renderer = renderer
        self.logo_inserter = logo_inserter
        self.processor = processor
        self.rotate_and_stretch = rotate_and_stretch
        self.target_size = target_size

        self.current_image_path = None
        self.base_image = None
        self.image_data_cache = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)

        # -------------------------------------------------------------
        # 1. PAINEL ESQUERDO: Lista de Imagens e Filtros
        # -------------------------------------------------------------
        left_group = QGroupBox("Imagens")
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(6, 8, 6, 6)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtro:"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["TODOS", "LEGEND", "SINGLE", "LOTE", "DATA", "SEM DATA", "CLEAN", "ROT"])
        filter_layout.addWidget(self.combo_filter)
        left_layout.addLayout(filter_layout)

        self.image_list = ImageListWidget()
        left_layout.addWidget(self.image_list)

        btn_layout = QHBoxLayout()
        self.btn_add_images = QPushButton("Adicionar...")
        self.btn_clear_images = QPushButton("Limpar")
        btn_layout.addWidget(self.btn_add_images)
        btn_layout.addWidget(self.btn_clear_images)
        left_layout.addLayout(btn_layout)

        left_group.setMinimumWidth(220)
        splitter.addWidget(left_group)

        # -------------------------------------------------------------
        # 2. PAINEL CENTRAL: Configurações da Legenda & Botão Gerar
        # -------------------------------------------------------------
        center_group = QGroupBox("Configurações da Legenda")
        center_layout = QVBoxLayout(center_group)
        center_layout.setContentsMargins(6, 8, 6, 6)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 4, 0)

        self.settings = LegendSettingsWidget(self.config)
        scroll_content_layout.addWidget(self.settings)

        self.check_apply_logo = QCheckBox("Inserir logo no canto superior direito")
        self.check_apply_logo.setChecked(True)
        scroll_content_layout.addWidget(self.check_apply_logo)

        scroll_content_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        center_layout.addWidget(scroll_area)

        self.btn_generate = QPushButton("Gerar Legendas nas Imagens Selecionadas")
        self.btn_generate.setMinimumHeight(42)
        self.btn_generate.setStyleSheet("font-weight: bold;")
        center_layout.addWidget(self.btn_generate)

        center_group.setMinimumWidth(350)
        splitter.addWidget(center_group)

        # -------------------------------------------------------------
        # 3. PAINEL DIREITO: Prévia ao Vivo da Imagem e Texto
        # -------------------------------------------------------------
        preview_group = QGroupBox("Prévia da Imagem")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(8, 8, 8, 8)

        self.preview = PreviewWidget()
        preview_layout.addWidget(self.preview)

        preview_group.setMinimumWidth(380)
        splitter.addWidget(preview_group)

        # Distribuição de proporções no splitter
        splitter.setSizes([230, 370, 560])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 1)

        root_layout.addWidget(splitter)

    def _connect_signals(self):
        self.btn_add_images.clicked.connect(self._on_add_images)
        self.btn_clear_images.clicked.connect(self._on_clear_images)
        self.btn_generate.clicked.connect(self._on_generate)
        self.settings.data_changed.connect(self._on_settings_data_changed)
        self.settings.ler_foto_requested.connect(self._on_ler_foto)
        self.combo_filter.currentTextChanged.connect(self._on_filter_changed)
        self.check_apply_logo.toggled.connect(self._update_preview)
        self.image_list.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_settings_data_changed(self):
        if self.current_image_path:
            self.image_data_cache[self.current_image_path] = self.settings.get_data()
        self._update_preview()

    def _on_selection_changed(self):
        selected_items = self.image_list.selectedItems()
        if selected_items:
            path_str = selected_items[0].text()
            if path_str != self.current_image_path:
                # 1. Salva os dados da imagem anterior no cache antes de trocar
                if self.current_image_path:
                    self.image_data_cache[self.current_image_path] = self.settings.get_data()

                # 2. Carrega a nova imagem base
                self.current_image_path = path_str
                self._load_base_image(path_str)

                # 3. Obtém os dados da nova imagem: do cache ou lendo os metadados do arquivo
                if path_str in self.image_data_cache:
                    self.settings.set_data(self.image_data_cache[path_str])
                else:
                    self._load_and_apply_metadata(path_str)
        else:
            if self.current_image_path:
                self.image_data_cache[self.current_image_path] = self.settings.get_data()
            self.current_image_path = None
            self.base_image = None
            self.settings.clear_fields()
            self.preview.clear_image()

        self._update_preview()

    def _load_and_apply_metadata(self, image_path):
        """Lê os metadados da imagem do disco e atualiza os campos e o cache."""
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
            self.settings.clear_fields()

        self.image_data_cache[image_path] = self.settings.get_data()

    def _load_base_image(self, path_str):
        if not path_str or not Path(path_str).exists():
            self.base_image = None
            return

        img = QImage(path_str)
        if img.isNull():
            self.base_image = None
            return

        if self.rotate_and_stretch:
            img = img.transformed(QTransform().rotate(-90), Qt.SmoothTransformation)
            target_w, target_h = self.target_size
            img = img.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        self.base_image = img

    def _on_filter_changed(self, filter_type):
        self.image_list.set_filter(filter_type)
        selected = self.image_list.selectedItems()
        if not selected or selected[0].isHidden():
            for i in range(self.image_list.count()):
                item = self.image_list.item(i)
                if not item.isHidden():
                    self.image_list.setCurrentItem(item)
                    break
            else:
                if self.current_image_path:
                    self.image_data_cache[self.current_image_path] = self.settings.get_data()
                self.current_image_path = None
                self.base_image = None
                self.settings.clear_fields()
                self.preview.clear_image()

    def _on_clear_images(self):
        self.image_list.clear()
        self.image_data_cache.clear()
        self.current_image_path = None
        self.base_image = None
        self.settings.clear_fields()
        self.preview.clear_image()
        self._update_preview()

    def _on_add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar Imagens", "",
            "Imagens (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)"
        )
        if files:
            self.image_list.add_files(files)
            if not self.image_list.selectedItems() and self.image_list.count() > 0:
                self.image_list.setCurrentRow(0)

    def _update_preview(self):
        text = self.settings.build_legend_text()
        self.preview.set_text(text)

        if self.base_image and not self.base_image.isNull():
            preview_img = self.base_image.copy()

            if self.check_apply_logo.isChecked() and self.logo_inserter and self.logo_inserter.logo_exists():
                self.logo_inserter.apply_logo_to_image(preview_img)

            font = self.settings.get_selected_font()
            self.renderer.apply_legend_to_image(preview_img, text, font)

            info = f"{Path(self.current_image_path).name} ({preview_img.width()}x{preview_img.height()})"
            self.preview.set_image(preview_img, info)
        else:
            self.preview.clear_image()

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
            self.image_data_cache[image_path] = self.settings.get_data()
            self._update_preview()
        else:
            QMessageBox.information(self, "Sem metadados", "Não foi possível extrair metadados desta imagem.")

    def _on_generate(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Aviso", "Nenhuma imagem selecionada na lista.")
            return

        # Sincroniza foto atual no cache
        if self.current_image_path:
            self.image_data_cache[self.current_image_path] = self.settings.get_data()

        apply_logo = self.check_apply_logo.isChecked()
        font = self.settings.get_selected_font()

        # Processamento seguro: cada imagem usa unicamente seus próprios dados
        if len(selected_items) == 1:
            img_path = selected_items[0].text()
            text = self.settings.build_legend_text()
            show_date = self.settings.check_data.isChecked()
            if self.rotate_and_stretch:
                prefix = '_IND_ROT' if show_date else '_IND_ROT_SD'
            else:
                prefix = '_IND' if show_date else '_IND_SD'

            try:
                results = self.processor.process_batch(
                    [img_path], text, font,
                    prefix=prefix,
                    apply_logo=apply_logo,
                    rotate_and_stretch=self.rotate_and_stretch,
                    target_size=self.target_size
                )
                if results:
                    QMessageBox.information(self, "Sucesso", f"Imagem legendada com sucesso:\n{Path(results[0]).name}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))
        else:
            results = []
            try:
                for item in selected_items:
                    img_path = item.text()
                    if img_path in self.image_data_cache:
                        data = self.image_data_cache[img_path]
                    else:
                        meta = MetadataParser.extract_custom_metadata(img_path)
                        temp_settings = LegendSettingsWidget(self.config)
                        if meta:
                            if 'servico' in meta:
                                meta['servico'] = MetadataParser.limpar_texto(meta['servico'])
                            if 'obra' in meta:
                                meta['obra'] = MetadataParser.limpar_texto(meta['obra'])
                            if 'lado' in meta:
                                meta['lado'] = MetadataParser.limpar_texto(meta['lado'])
                            temp_settings.fill_from_metadata(meta)
                        else:
                            temp_settings.clear_fields()
                        data = temp_settings.get_data()

                    text = self.settings.build_legend_text(data)
                    show_date = data.get("show_date", True)
                    if self.rotate_and_stretch:
                        prefix = '_IND_ROT' if show_date else '_IND_ROT_SD'
                    else:
                        prefix = '_IND' if show_date else '_IND_SD'

                    res = self.processor.process_batch(
                        [img_path], text, font,
                        prefix=prefix,
                        apply_logo=apply_logo,
                        rotate_and_stretch=self.rotate_and_stretch,
                        target_size=self.target_size
                    )
                    results.extend(res)

                QMessageBox.information(self, "Sucesso", f"{len(results)} imagens processadas.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))