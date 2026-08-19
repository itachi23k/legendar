from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QFileDialog, QMessageBox, QCheckBox, QLabel,
                               QComboBox, QLineEdit, QRadioButton, QButtonGroup,
                               QGroupBox, QGridLayout, QProgressBar, QScrollArea,
                               QDateEdit, QFrame, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from core.metadata_parser import MetadataParser
from core.legend_renderer import LegendRenderer
from core.logo_inserter import LogoInserter
from core.estaca_adjuster import EstacaAdjuster
from core.exif_writer import ExifWriter
from gui.widgets.estaca_adjust_widget import EstacaAdjustWidget
from pathlib import Path
from datetime import datetime

class DateRuleWidget(QWidget):
    """Widget representando uma única regra de data."""
    remove_requested = Signal(object)  # envia a própria instância

    def __init__(self, original_date=None, new_date=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("De:"))
        self.original_date_edit = QDateEdit()
        self.original_date_edit.setCalendarPopup(True)
        self.original_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.original_date_edit.setDate(original_date if original_date else QDate.currentDate())
        layout.addWidget(self.original_date_edit)

        layout.addWidget(QLabel("Para:"))
        self.new_date_edit = QDateEdit()
        self.new_date_edit.setCalendarPopup(True)
        self.new_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.new_date_edit.setDate(new_date if new_date else QDate.currentDate())
        layout.addWidget(self.new_date_edit)

        self.btn_remove = QPushButton("−")
        self.btn_remove.setFixedWidth(40)
        self.btn_remove.setToolTip("Remover regra")
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self.btn_remove)

    def get_rule(self):
        """Retorna a regra como dict com strings no formato dd/mm/yyyy."""
        orig = self.original_date_edit.date().toString("dd/MM/yyyy")
        nova = self.new_date_edit.date().toString("dd/MM/yyyy")
        return {"original": orig, "new": nova}


class BatchProcessorThread(QThread):
    """Thread para processamento em lote."""
    progress = Signal(int, int, str)
    finished = Signal(int, int, int)  # sucessos, total, ignorados
    error = Signal(str)

    def __init__(self, files, settings, renderer, logo_inserter):
        super().__init__()
        self.files = files
        self.settings = settings
        self.renderer = renderer
        self.logo_inserter = logo_inserter
        self.ignored_count = 0

    def run(self):
        success_count = 0
        total = len(self.files)

        for i, file_path in enumerate(self.files):
            try:
                self.progress.emit(i + 1, total, Path(file_path).name)

                meta = MetadataParser.extract_custom_metadata(file_path)
                if meta is None:
                    meta = {
                        'obra': 'DADO AUSENTE',
                        'servico': 'DADO AUSENTE',
                        'estaca': '0',
                        'lado': '-',
                        'utm': '20M 000000 0000000',
                        'data': ''
                    }

                # Aplicar regras de data (se estiver no modo regras)
                if self.settings.get('use_date_rules', False):
                    meta = self._apply_date_rules(meta)
                    if meta is None:
                        self.ignored_count += 1
                        continue  # pula o arquivo

                final_data = self._apply_overrides(meta)

                estaca_adjustment = self.settings.get('estaca_adjustment', 0)
                if estaca_adjustment != 0:
                    final_data['estaca'] = EstacaAdjuster.apply_adjustment_to_text(
                        final_data['estaca'], estaca_adjustment
                    )

                legend_text = self._build_legend_text(final_data)
                output_path = self._get_output_path(file_path)

                if self.settings.get('apply_logo', False) and self.logo_inserter.logo_exists():
                    success = LogoInserter.composite_logo_and_legend(
                        file_path, output_path, self.logo_inserter,
                        self.renderer, legend_text, "Araboto-Normal"
                    )
                else:
                    success = self.renderer.render(
                        file_path, output_path, legend_text, "Araboto-Normal"
                    )

                if success:
                    ExifWriter.update_user_comment_from_metadata(output_path, final_data)
                    success_count += 1

            except Exception as e:
                self.error.emit(f"Erro ao processar {file_path}: {str(e)}")

        self.finished.emit(success_count, total, self.ignored_count)

    def _apply_date_rules(self, meta):
        """Aplica as regras de data. Retorna meta atualizado ou None se deve ignorar."""
        rules = self.settings.get('date_rules', [])
        ignore_non_matching = self.settings.get('ignore_non_matching', True)

        original_date_str = meta.get('data', '').strip()
        # Normalizar formato: assume dd/mm/yyyy
        if not original_date_str:
            if ignore_non_matching:
                return None
            return meta

        for rule in rules:
            if original_date_str == rule['original']:
                meta['data'] = rule['new']
                return meta

        # Nenhuma regra correspondeu
        if ignore_non_matching:
            return None
        return meta

    def _apply_overrides(self, meta):
        final = {
            'obra': meta.get('obra', 'DADO AUSENTE'),
            'servico': meta.get('servico', 'DADO AUSENTE'),
            'estaca': meta.get('estaca', '0'),
            'lado': meta.get('lado', '-'),
            'utm': meta.get('utm', '20M 000000 0000000'),
            'data': meta.get('data', '')
        }

        if self.settings.get('override_obra_enabled', False):
            override_obra = self.settings.get('override_obra', '')
            if override_obra != '[MANTER O DA FOTO]':
                final['obra'] = override_obra

        if self.settings.get('override_estaca_enabled', False):
            final['estaca'] = self.settings.get('override_estaca', '0')

        if self.settings.get('override_lado_enabled', False):
            final['lado'] = self.settings.get('override_lado', 'D')

        if self.settings.get('override_servico_enabled', False):
            final['servico'] = self.settings.get('override_servico', '')
        else:
            final['servico'] = MetadataParser.corrigir_caracteres_especiais(
                final['servico'].upper()
            )

        if self.settings.get('override_data_enabled', False):
            final['data'] = self.settings.get('override_data', '')

        return final

    def _build_legend_text(self, data):
        show_date = self.settings.get('show_date', True)

        lines = [
            data['utm'],
            "BR-319/AM",
            data['obra'],
            f"ESTACA: {data['estaca']}",
            f"LADO: {data['lado']}",
            f"SERVIÇO: {data['servico']}",
        ]

        if show_date:
            lines.append(data['data'] if data['data'] else " ")

        return "\r".join(lines)

    def _get_output_path(self, input_path):
        path = Path(input_path)

        if self.settings.get('is_main_folder_mode', False):
            new_name = path.stem.replace('CLEAN', 'MODED', 1)
            if 'MODED' not in new_name:
                new_name = f"{path.stem}_MODED"
            return str(path.with_name(f"{new_name}{path.suffix}"))

        output_folder = self.settings.get('output_folder', '')
        prefix = self.settings.get('output_prefix', '_MODED')

        if output_folder:
            out_dir = Path(output_folder)
            out_dir.mkdir(parents=True, exist_ok=True)
            return str(out_dir / f"{path.stem}{prefix}{path.suffix}")
        else:
            return str(path.with_name(f"{path.stem}{prefix}{path.suffix}"))


class BatchEditorWidget(QWidget):
    """Aba para edição em lote."""

    def __init__(self, config, renderer, logo_inserter, processor):
        super().__init__()
        self.config = config
        self.renderer = renderer
        self.logo_inserter = logo_inserter
        self.processor = processor
        self.date_rules = []  # lista de DateRuleWidget

        self._init_ui()
        self._load_preferences()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # MODO DE OPERAÇÃO
        mode_group = QGroupBox("Modo de Entrada")
        mode_layout = QVBoxLayout()

        mode_row1 = QHBoxLayout()
        self.radio_files = QRadioButton("Selecionar Arquivos Manuais")
        self.radio_folder = QRadioButton("Processar Pasta Inteira")
        self.radio_files.setChecked(True)
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_files)
        self.mode_group.addButton(self.radio_folder)
        mode_row1.addWidget(self.radio_files)
        mode_row1.addWidget(self.radio_folder)

        mode_row2 = QHBoxLayout()
        self.radio_main_folder = QRadioButton("Modo Pasta Principal (recursivo)")
        self.mode_group.addButton(self.radio_main_folder)
        mode_row2.addWidget(self.radio_main_folder)
        mode_row2.addWidget(QLabel("Procura arquivos com 'CLEAN' no nome em subpastas"))

        mode_row3 = QHBoxLayout()
        self.radio_rules = QRadioButton("Modo Regras de Data")
        self.mode_group.addButton(self.radio_rules)
        mode_row3.addWidget(self.radio_rules)
        mode_row3.addWidget(QLabel("Aplica regras de data durante a edição"))

        mode_layout.addLayout(mode_row1)
        mode_layout.addLayout(mode_row2)
        mode_layout.addLayout(mode_row3)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # ÁREA DE REGRAS DE DATA (visível apenas no modo regras)
        self.rules_group = QGroupBox("Regras de Data")
        rules_layout = QVBoxLayout()
        self.rules_container = QVBoxLayout()
        self.rules_container.setSpacing(5)

        # Área rolável para as regras
        self.rules_scroll = QScrollArea()
        self.rules_scroll.setWidgetResizable(True)
        self.rules_widget = QWidget()
        self.rules_widget.setLayout(self.rules_container)
        self.rules_scroll.setWidget(self.rules_widget)
        self.rules_scroll.setMinimumHeight(120)
        self.rules_scroll.setMaximumHeight(220)
        rules_layout.addWidget(self.rules_scroll)

        # Botão para adicionar regra
        btn_add_rule = QPushButton("+ Adicionar Regra")
        btn_add_rule.clicked.connect(self._on_add_rule)
        rules_layout.addWidget(btn_add_rule, alignment=Qt.AlignLeft)

        # Checkbox ignorar sem correspondência
        self.check_ignore_non_matching = QCheckBox("Ignorar arquivos sem correspondência de data")
        self.check_ignore_non_matching.setChecked(True)
        rules_layout.addWidget(self.check_ignore_non_matching)

        self.rules_group.setLayout(rules_layout)
        layout.addWidget(self.rules_group)
        self.rules_group.setVisible(False)  # oculto por padrão

        # VISIBILIDADE GERAL
        visibility_group = QGroupBox("Visibilidade Geral")
        visibility_layout = QHBoxLayout()
        self.check_logo = QCheckBox("Inserir Logo LCM")
        self.check_logo.setChecked(True)
        self.check_date = QCheckBox("Exibir Data na Legenda")
        self.check_date.setChecked(True)
        visibility_layout.addWidget(self.check_logo)
        visibility_layout.addWidget(self.check_date)
        visibility_group.setLayout(visibility_layout)
        layout.addWidget(visibility_group)

        # AJUSTE DE ESTACA
        estaca_group = QGroupBox("Ajuste de Estaca")
        estaca_layout = QVBoxLayout()
        self.estaca_adjust = EstacaAdjustWidget()
        estaca_layout.addWidget(self.estaca_adjust)
        estaca_group.setLayout(estaca_layout)
        layout.addWidget(estaca_group)

        # SOBRESCRITAS
        overrides_group = QGroupBox("Forçar Dados (Ignorar Metadados)")
        overrides_layout = QGridLayout()

        self.check_override_obra = QCheckBox("Contrato:")
        self.combo_obra = QComboBox()
        self.combo_obra.addItems(["[MANTER O DA FOTO]", "TT-563/2024", "SR-592/2020", "SR-593/2020"])
        self.combo_obra.setEnabled(False)
        overrides_layout.addWidget(self.check_override_obra, 0, 0)
        overrides_layout.addWidget(self.combo_obra, 0, 1)

        self.check_override_estaca = QCheckBox("Estaca:")
        self.edit_estaca = QLineEdit("0+00,00")
        self.edit_estaca.setEnabled(False)
        overrides_layout.addWidget(self.check_override_estaca, 1, 0)
        overrides_layout.addWidget(self.edit_estaca, 1, 1)

        self.check_override_lado = QCheckBox("Lado:")
        self.combo_lado = QComboBox()
        self.combo_lado.addItems(["D", "E", "D/E", "EIXO"])
        self.combo_lado.setEnabled(False)
        overrides_layout.addWidget(self.check_override_lado, 2, 0)
        overrides_layout.addWidget(self.combo_lado, 2, 1)

        self.check_override_servico = QCheckBox("Serviço:")
        self.combo_servico = QComboBox()
        self.combo_servico.addItems([
            "APLICAÇÃO DE BGS", "APLICAÇÃO DE CBUQ", "CAMADA DE MACADAME SECO",
            "CAMADA DE REFORÇO", "CANTEIRO DE OBRAS", "CHECKLIST DE EQUIPAMENTO",
            "CORREÇÃO DE ENROCAMENTO", "DESCARREGAMENTO DE BALSA", "ENROCAMENTO",
            "EROSÃO", "ESTOQUE DE MATERIAL", "EXECUÇÃO DE BUEIRO",
            "EXECUÇÃO DE PONTILHÃO", "FAIXA DE DOMÍNIO", "HIDROSSEMEADURA",
            "IMPLANTAÇÃO DE PLACAS", "IMPRIMAÇÃO", "LANÇAMENTO DE BGS",
            "LASTRO DE BRITA", "LIMPEZA DE SARJETA", "LIMPEZA DE VALA DE DRENAGEM",
            "PATRULHA DE EQUIPAMENTOS", "PINTURA DE LIGAÇÃO", "PLANTIO DE GRAMA",
            "PONTE DE MADEIRA", "RECOMPOSIÇÃO MECANIZADA DE ATERRO",
            "REFORMA DE PONTE", "REGULARIZAÇÃO DE SUBLEITO", "REMENDO PROFUNDO",
            "REMOÇÃO DE ÁRVORES", "REMOÇÃO E TRANSPORTE", "REVESTIMENTO PRIMÁRIO 01",
            "REVESTIMENTO PRIMÁRIO 02", "ROÇADA", "SINALIZAÇÃO TEMPORÁRIA",
            "SINALIZAÇÃO VERTICAL", "TAPA BURACO", "TEMPO CHUVOSO", "VALA DE DRENAGEM"
        ])
        self.combo_servico.setEnabled(False)
        overrides_layout.addWidget(self.check_override_servico, 3, 0)
        overrides_layout.addWidget(self.combo_servico, 3, 1)

        self.check_override_data = QCheckBox("Data:")
        self.edit_data = QLineEdit("DD/MM/AAAA")
        self.edit_data.setEnabled(False)
        overrides_layout.addWidget(self.check_override_data, 4, 0)
        overrides_layout.addWidget(self.edit_data, 4, 1)

        overrides_group.setLayout(overrides_layout)
        layout.addWidget(overrides_group)

        # SELEÇÃO DE ARQUIVOS
        selection_group = QGroupBox("Seleção de Arquivos")
        selection_layout = QVBoxLayout()
        self.btn_select = QPushButton("Selecionar Arquivos...")
        self.lbl_selection = QLabel("Nenhum arquivo selecionado")
        selection_layout.addWidget(self.btn_select)
        selection_layout.addWidget(self.lbl_selection)
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        # PASTA DE SAÍDA
        output_group = QGroupBox("Pasta de Saída")
        output_layout = QHBoxLayout()
        self.edit_output_folder = QLineEdit()
        self.edit_output_folder.setPlaceholderText("Pasta de destino (opcional)")
        self.btn_select_output = QPushButton("Selecionar...")
        output_layout.addWidget(self.edit_output_folder)
        output_layout.addWidget(self.btn_select_output)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # PROGRESSO
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # BOTÃO PROCESSAR
        self.btn_process = QPushButton("Iniciar Processamento em Lote")
        self.btn_process.setMinimumHeight(40)
        layout.addWidget(self.btn_process)

    def _connect_signals(self):
        self.check_override_obra.toggled.connect(self.combo_obra.setEnabled)
        self.check_override_estaca.toggled.connect(self.edit_estaca.setEnabled)
        self.check_override_lado.toggled.connect(self.combo_lado.setEnabled)
        self.check_override_servico.toggled.connect(self.combo_servico.setEnabled)
        self.check_override_data.toggled.connect(self.edit_data.setEnabled)

        self.radio_files.toggled.connect(self._on_mode_changed)
        self.radio_folder.toggled.connect(self._on_mode_changed)
        self.radio_main_folder.toggled.connect(self._on_mode_changed)
        self.radio_rules.toggled.connect(self._on_mode_changed)

        self.btn_select.clicked.connect(self._on_select_files)
        self.btn_select_output.clicked.connect(self._on_select_output)
        self.btn_process.clicked.connect(self._on_process)

    def _on_mode_changed(self):
        # Atualiza texto do botão conforme o modo
        if self.radio_files.isChecked():
            self.btn_select.setText("Selecionar Arquivos...")
        elif self.radio_main_folder.isChecked():
            self.btn_select.setText("Selecionar Pasta Principal...")
        elif self.radio_rules.isChecked():
            self.btn_select.setText("Selecionar Pasta Principal...")
        else:
            self.btn_select.setText("Selecionar Pasta...")

        # Mostra/esconde a área de regras
        self.rules_group.setVisible(self.radio_rules.isChecked())

    def _on_add_rule(self):
        """Adiciona uma nova linha de regra de data."""
        rule_widget = DateRuleWidget()
        rule_widget.remove_requested.connect(self._on_remove_rule)
        self.rules_container.addWidget(rule_widget)
        self.date_rules.append(rule_widget)

    def _on_remove_rule(self, widget):
        """Remove uma regra de data."""
        if widget in self.date_rules:
            self.date_rules.remove(widget)
            self.rules_container.removeWidget(widget)
            widget.deleteLater()

    def _on_select_files(self):
        if self.radio_files.isChecked():
            files, _ = QFileDialog.getOpenFileNames(
                self, "Selecionar Imagens", "",
                "Imagens (*.jpg *.jpeg *.png *.tif *.tiff)"
            )
            if files:
                self.selected_files = files
                self.lbl_selection.setText(f"{len(files)} arquivo(s) selecionado(s)")

        elif self.radio_main_folder.isChecked() or self.radio_rules.isChecked():
            folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta Principal")
            if folder:
                self.selected_files = self._find_clean_files_recursive(folder)
                self.main_folder = folder
                self.lbl_selection.setText(
                    f"Pasta Principal: {folder}\n"
                    f"Encontrados: {len(self.selected_files)} arquivos com 'CLEAN'"
                )

        else:
            folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Entrada")
            if folder:
                extensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff']
                self.selected_files = [
                    str(f) for f in Path(folder).iterdir()
                    if f.suffix.lower() in extensions
                ]
                self.lbl_selection.setText(f"Pasta: {folder} ({len(self.selected_files)} imagens)")

    def _find_clean_files_recursive(self, folder):
        extensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff']
        clean_files = []
        folder_path = Path(folder)
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                if file_path.suffix.lower() in extensions:
                    if 'CLEAN' in file_path.stem.upper():
                        clean_files.append(str(file_path))
        return clean_files

    def _on_select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saída")
        if folder:
            self.edit_output_folder.setText(folder)

    def _on_process(self):
        if not hasattr(self, 'selected_files') or not self.selected_files:
            QMessageBox.warning(self, "Aviso", "Selecione os arquivos ou pasta de entrada.")
            return

        settings = {
            'apply_logo': self.check_logo.isChecked(),
            'show_date': self.check_date.isChecked(),
            'estaca_adjustment': self.estaca_adjust.get_adjustment(),
            'override_obra_enabled': self.check_override_obra.isChecked(),
            'override_obra': self.combo_obra.currentText(),
            'override_estaca_enabled': self.check_override_estaca.isChecked(),
            'override_estaca': self.edit_estaca.text(),
            'override_lado_enabled': self.check_override_lado.isChecked(),
            'override_lado': self.combo_lado.currentText(),
            'override_servico_enabled': self.check_override_servico.isChecked(),
            'override_servico': self.combo_servico.currentText(),
            'override_data_enabled': self.check_override_data.isChecked(),
            'override_data': self.edit_data.text(),
            'output_folder': self.edit_output_folder.text(),
            'output_prefix': '_MODED',
            'is_main_folder_mode': self.radio_main_folder.isChecked(),
            'use_date_rules': self.radio_rules.isChecked(),
            'date_rules': [w.get_rule() for w in self.date_rules],
            'ignore_non_matching': self.check_ignore_non_matching.isChecked()
        }

        self._save_preferences(settings)

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.selected_files))
        self.progress_bar.setValue(0)
        self.btn_process.setEnabled(False)

        self.thread = BatchProcessorThread(
            self.selected_files, settings,
            self.renderer, self.logo_inserter
        )
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.error.connect(self._on_error)
        self.thread.start()

    def _on_progress(self, current, total, filename):
        self.progress_bar.setValue(current)
        self.lbl_selection.setText(f"Processando {current}/{total}: {filename}")

    def _on_finished(self, success_count, total, ignored_count):
        self.progress_bar.setVisible(False)
        self.btn_process.setEnabled(True)
        msg = f"Processadas: {success_count}/{total}\nIgnoradas: {ignored_count}"
        self.lbl_selection.setText(msg)
        QMessageBox.information(self, "Processamento Concluído", msg)

    def _on_error(self, error_msg):
        QMessageBox.warning(self, "Erro", error_msg)

    def _save_preferences(self, settings):
        self.config.set('batch_preferences', settings)

    def _load_preferences(self):
        prefs = self.config.get('batch_preferences', None)
        if prefs:
            self.check_logo.setChecked(prefs.get('apply_logo', True))
            self.check_date.setChecked(prefs.get('show_date', True))

            if prefs.get('override_obra_enabled', False):
                self.check_override_obra.setChecked(True)
                idx = self.combo_obra.findText(prefs.get('override_obra', ''))
                if idx >= 0:
                    self.combo_obra.setCurrentIndex(idx)

            if prefs.get('override_estaca_enabled', False):
                self.check_override_estaca.setChecked(True)
                self.edit_estaca.setText(prefs.get('override_estaca', ''))

            if prefs.get('override_lado_enabled', False):
                self.check_override_lado.setChecked(True)
                idx = self.combo_lado.findText(prefs.get('override_lado', ''))
                if idx >= 0:
                    self.combo_lado.setCurrentIndex(idx)

            if prefs.get('override_servico_enabled', False):
                self.check_override_servico.setChecked(True)
                idx = self.combo_servico.findText(prefs.get('override_servico', ''))
                if idx >= 0:
                    self.combo_servico.setCurrentIndex(idx)

            if prefs.get('override_data_enabled', False):
                self.check_override_data.setChecked(True)
                self.edit_data.setText(prefs.get('override_data', ''))

            if prefs.get('output_folder', ''):
                self.edit_output_folder.setText(prefs.get('output_folder', ''))

            # Restaurar regras de data, se existirem
            rules = prefs.get('date_rules', [])
            for rule in rules:
                orig = QDate.fromString(rule['original'], "dd/MM/yyyy")
                nova = QDate.fromString(rule['new'], "dd/MM/yyyy")
                self._on_add_rule()
                w = self.date_rules[-1]
                w.original_date_edit.setDate(orig)
                w.new_date_edit.setDate(nova)

            if prefs.get('use_date_rules', False):
                self.radio_rules.setChecked(True)