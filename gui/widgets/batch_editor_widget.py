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
from gui.dialogs.date_rules_dialog import DateRulesDialog
from pathlib import Path
from datetime import datetime

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
                output_path = self._get_output_path(file_path, final_data)

                rotate_and_stretch = self.settings.get('rotate_and_stretch', False)
                target_size = self.settings.get('target_size', (1440, 1080))

                if self.settings.get('apply_logo', False) and self.logo_inserter.logo_exists():
                    success = LogoInserter.composite_logo_and_legend(
                        file_path, output_path, self.logo_inserter,
                        self.renderer, legend_text, "Araboto-Normal",
                        rotate_and_stretch=rotate_and_stretch,
                        target_size=target_size
                    )
                else:
                    success = self.renderer.render(
                        file_path, output_path, legend_text, "Araboto-Normal",
                        rotate_and_stretch=rotate_and_stretch,
                        target_size=target_size
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
                action = rule.get('action', 'alterar')
                if action == 'omitir':
                    meta['data'] = ''
                    meta['omit_date'] = True
                else:
                    meta['data'] = rule['new']
                    meta['omit_date'] = False
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
            'data': meta.get('data', ''),
            'omit_date': meta.get('omit_date', False)
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
            final['omit_date'] = False

        return final

    def _build_legend_text(self, data):
        show_date = self.settings.get('show_date', True)
        if data.get('omit_date', False):
            show_date = False

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
        else:
            lines.append(" ")

        return "\r".join(lines)

    def _get_output_path(self, input_path, final_data=None):
        path = Path(input_path)
        show_date = self.settings.get('show_date', True)
        if final_data and final_data.get('omit_date', False):
            show_date = False

        is_rot = self.settings.get('rotate_and_stretch', False)

        output_folder = self.settings.get('output_folder', '')

        if self.settings.get('is_main_folder_mode', False):
            if is_rot:
                replace_to = 'MODED_ROT' if show_date else 'MODED_ROT_SD'
            else:
                replace_to = 'MODED' if show_date else 'MODED_SD'
            new_name = path.stem.replace('CLEAN', replace_to, 1)
            if replace_to not in new_name:
                new_name = f"{path.stem}_{replace_to}"
            if output_folder:
                out_dir = Path(output_folder)
                out_dir.mkdir(parents=True, exist_ok=True)
                return str(out_dir / f"{new_name}{path.suffix}")
            return str(path.with_name(f"{new_name}{path.suffix}"))


        if self.settings.get('use_date_rules', False):
            if is_rot:
                prefix = '_REG_ROT' if show_date else '_REG_ROT_SD'
            else:
                prefix = '_REG' if show_date else '_REG_SD'
        else:
            if is_rot:
                prefix = '_LOTE_ROT' if show_date else '_LOTE_ROT_SD'
            else:
                prefix = '_LOTE' if show_date else '_LOTE_SD'

        if output_folder:
            out_dir = Path(output_folder)
            out_dir.mkdir(parents=True, exist_ok=True)
            return str(out_dir / f"{path.stem}{prefix}{path.suffix}")
        else:
            return str(path.with_name(f"{path.stem}{prefix}{path.suffix}"))


class BatchEditorWidget(QWidget):
    """Aba para edição em lote."""

    def __init__(self, config, renderer, logo_inserter, processor,
                 rotate_and_stretch=False, target_size=(1440, 1080)):
        super().__init__()
        self.config = config
        self.renderer = renderer
        self.logo_inserter = logo_inserter
        self.processor = processor
        self.rotate_and_stretch = rotate_and_stretch
        self.target_size = target_size
        self.pref_key = 'batch_camera_preferences' if rotate_and_stretch else 'batch_preferences'
        self.date_rules = []
        self.ignore_non_matching = True

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

        # CONFIGURAÇÃO DE REGRAS DE DATA
        self.rules_group = QGroupBox("Regras de Data")
        rules_layout = QVBoxLayout()
        self.lbl_rules = QLabel("Nenhuma regra configurada")
        self.btn_configure_rules = QPushButton("Configurar regras de data...")
        self.btn_configure_rules.clicked.connect(self._open_date_rules_dialog)
        rules_layout.addWidget(self.lbl_rules)
        rules_layout.addWidget(self.btn_configure_rules, alignment=Qt.AlignLeft)

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
            "LASTRO DE BRITA", "LASTRO DE AREIA", "LIMPEZA DE SARJETA", "LIMPEZA DE VALA DE DRENAGEM",
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

        self.btn_pin_output = QPushButton("📌")
        self.btn_pin_output.setCheckable(True)
        self.btn_pin_output.setFixedWidth(32)
        self.btn_pin_output.setToolTip(
            "Salvar na pasta de origem (padrão)\n"
            "Clique para definir uma pasta de saída diferente"
        )

        self.edit_output_folder = QLineEdit()
        self.edit_output_folder.setPlaceholderText("Mesma pasta de origem de cada foto")
        self.edit_output_folder.setEnabled(False)

        self.btn_select_output = QPushButton("Selecionar...")
        self.btn_select_output.setEnabled(False)

        output_layout.addWidget(self.btn_pin_output)
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
        self.btn_pin_output.toggled.connect(self._on_pin_toggled)
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

    def _open_date_rules_dialog(self):
        dialog = DateRulesDialog(
            self,
            initial_rules=self.date_rules,
            ignore_non_matching=self.ignore_non_matching
        )
        if dialog.exec():
            settings = dialog.get_settings()
            self.date_rules = settings['date_rules']
            self.ignore_non_matching = settings['ignore_non_matching']
            self._update_rules_summary()

    def _update_rules_summary(self):
        if not self.date_rules:
            self.lbl_rules.setText("Nenhuma regra configurada")
            return

        omitted = sum(rule.get('action') == 'omitir' for rule in self.date_rules)
        altered = len(self.date_rules) - omitted
        self.lbl_rules.setText(
            f"{len(self.date_rules)} regra(s): {altered} alteração(ões), "
            f"{omitted} omissão(ões)"
        )

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

    def _on_pin_toggled(self, checked):
        """Habilita/desabilita a seleção de pasta de saída personalizada."""
        self.edit_output_folder.setEnabled(checked)
        self.btn_select_output.setEnabled(checked)
        if checked:
            self.btn_pin_output.setToolTip(
                "Pasta de saída personalizada ativada\n"
                "Clique para voltar ao padrão (mesma pasta de origem)"
            )
        else:
            self.edit_output_folder.clear()
            self.btn_pin_output.setToolTip(
                "Salvar na pasta de origem (padrão)\n"
                "Clique para definir uma pasta de saída diferente"
            )

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
            'output_folder': self.edit_output_folder.text() if self.btn_pin_output.isChecked() else '',
            'output_prefix': '_MODED',
            'is_main_folder_mode': self.radio_main_folder.isChecked(),
            'use_date_rules': self.radio_rules.isChecked(),
            'date_rules': self.date_rules,
            'ignore_non_matching': self.ignore_non_matching,
            'rotate_and_stretch': self.rotate_and_stretch,
            'target_size': self.target_size
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
        settings['pin_output_active'] = self.btn_pin_output.isChecked()
        self.config.set(self.pref_key, settings)

    def _load_preferences(self):
        prefs = self.config.get(self.pref_key, None)
        if not prefs and self.rotate_and_stretch:
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

            if prefs.get('pin_output_active', False):
                self.btn_pin_output.setChecked(True)  # triggers _on_pin_toggled
                if prefs.get('output_folder', ''):
                    self.edit_output_folder.setText(prefs.get('output_folder', ''))

            self.date_rules = prefs.get('date_rules', [])
            self.ignore_non_matching = prefs.get('ignore_non_matching', True)
            self._update_rules_summary()

            if prefs.get('use_date_rules', False):
                self.radio_rules.setChecked(True)