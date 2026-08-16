from PySide6.QtWidgets import (QWidget, QFormLayout, QComboBox, QLineEdit,
                               QCheckBox, QTextEdit, QPushButton, QHBoxLayout,
                               QVBoxLayout, QLabel, QMessageBox)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFontDatabase

from core.config_manager import ConfigManager
from core.txt_reader import EstacasTXTReader
from core.font_manager import FontManager
from core.estaca_adjuster import EstacaAdjuster
from gui.dialogs.coordinate_converter_dialog import CoordinateConverterDialog
from gui.widgets.estaca_adjust_widget import EstacaAdjustWidget

class LegendSettingsWidget(QWidget):
    data_changed = Signal()
    ler_foto_requested = Signal()

    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self._init_ui()
        self._load_values_from_config()
        self._connect_signals()
        self._populate_fonts()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.obras = ["TT-563/2024", "SR-592/2020", "SR-593/2020"]
        self.servicos = [
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
        ]
        self.meses = [f"{i:02d}" for i in range(1, 13)]
        self.lados = ["E", "D", "D/E", "EIXO"]

        form = QFormLayout()

        self.combo_obra = QComboBox()
        self.combo_obra.addItems(self.obras)
        form.addRow("Obra:", self.combo_obra)

        self.combo_servico = QComboBox()
        self.combo_servico.addItems(self.servicos)
        form.addRow("Serviço:", self.combo_servico)

        self.edit_utm = QLineEdit()
        form.addRow("Coordenada UTM:", self.edit_utm)

        hbox_estaca = QHBoxLayout()
        self.edit_estaca = QLineEdit()
        self.edit_estaca.setMaximumWidth(100)
        self.combo_lado = QComboBox()
        self.combo_lado.addItems(self.lados)
        self.btn_buscar_utm = QPushButton("Buscar UTM")
        hbox_estaca.addWidget(self.edit_estaca)
        hbox_estaca.addWidget(self.combo_lado)
        hbox_estaca.addWidget(self.btn_buscar_utm)
        form.addRow("Estaca/Lado:", hbox_estaca)

        # Ajuste de estaca
        self.estaca_adjust = EstacaAdjustWidget()
        form.addRow("", self.estaca_adjust)

        hbox_data = QHBoxLayout()
        self.edit_dia = QLineEdit()
        self.edit_dia.setMaxLength(2)
        self.edit_dia.setMaximumWidth(40)
        self.combo_mes = QComboBox()
        self.combo_mes.addItems(self.meses)
        self.edit_ano = QLineEdit()
        self.edit_ano.setMaxLength(4)
        self.edit_ano.setMaximumWidth(60)
        hbox_data.addWidget(self.edit_dia)
        hbox_data.addWidget(self.combo_mes)
        hbox_data.addWidget(self.edit_ano)
        form.addRow("Dia/Mês/Ano:", hbox_data)

        self.check_data = QCheckBox("Exibir data no texto final")
        form.addRow("", self.check_data)

        self.edit_obs = QTextEdit()
        self.edit_obs.setMaximumHeight(80)
        form.addRow("Observação:", self.edit_obs)

        layout.addLayout(form)

        hbox_fonte = QHBoxLayout()
        lbl_fonte = QLabel("Fonte:")
        self.combo_fonte = QComboBox()
        hbox_fonte.addWidget(lbl_fonte)
        hbox_fonte.addWidget(self.combo_fonte)
        layout.addLayout(hbox_fonte)

        hbox_buttons = QHBoxLayout()
        self.btn_ler_foto = QPushButton("Ler Dados da Foto")
        self.btn_conv_coord = QPushButton("Converter Coordenada")
        hbox_buttons.addWidget(self.btn_ler_foto)
        hbox_buttons.addWidget(self.btn_conv_coord)
        layout.addLayout(hbox_buttons)

    def _connect_signals(self):
        for combo in [self.combo_obra, self.combo_servico, self.combo_lado, self.combo_mes]:
            combo.currentIndexChanged.connect(self._emit_data_changed)
        for edit in [self.edit_utm, self.edit_estaca, self.edit_dia, self.edit_ano]:
            edit.textChanged.connect(self._emit_data_changed)
        self.check_data.toggled.connect(self._emit_data_changed)
        self.edit_obs.textChanged.connect(self._emit_data_changed)
        self.combo_fonte.currentIndexChanged.connect(self._emit_data_changed)
        self.estaca_adjust.adjustment_changed.connect(self._emit_data_changed)

        self.btn_buscar_utm.clicked.connect(self._on_buscar_utm)
        self.btn_conv_coord.clicked.connect(self._on_converter_coordenada)
        self.btn_ler_foto.clicked.connect(self._on_ler_foto)

    def _populate_fonts(self):
        araboto_family = FontManager.load_araboto_font()
        font_db = QFontDatabase()
        families = font_db.families()

        if araboto_family and araboto_family not in families:
            self.combo_fonte.addItem(araboto_family)

        self.combo_fonte.addItems(families)

        if araboto_family:
            idx = self.combo_fonte.findText(araboto_family)
            if idx >= 0:
                self.combo_fonte.setCurrentIndex(idx)
        else:
            idx = self.combo_fonte.findText("Arial")
            if idx >= 0:
                self.combo_fonte.setCurrentIndex(idx)

    def _load_values_from_config(self):
        self.combo_obra.setCurrentIndex(self.config.get("obra_idx", 0))
        self.combo_servico.setCurrentIndex(self.config.get("servico_idx", 0))
        self.edit_utm.setText(self.config.get("last_utm", ""))
        self.edit_estaca.setText(self.config.get("estaca", ""))
        idx = self.combo_lado.findText(self.config.get("lado", "D"))
        if idx >= 0:
            self.combo_lado.setCurrentIndex(idx)
        self.edit_dia.setText(self.config.get("dia", ""))
        mes_str = str(self.config.get("mes_idx", 1)).zfill(2)
        idx = self.combo_mes.findText(mes_str)
        if idx >= 0:
            self.combo_mes.setCurrentIndex(idx)
        self.edit_ano.setText(self.config.get("ano", ""))
        self.check_data.setChecked(self.config.get("show_date", True))
        self.edit_obs.setPlainText(self.config.get("obs", ""))

    def _emit_data_changed(self):
        self.data_changed.emit()

    def _on_buscar_utm(self):
        obra = self.combo_obra.currentText()
        estaca = self.edit_estaca.text().strip()
        if not estaca:
            QMessageBox.warning(self, "Aviso", "Digite um número de estaca.")
            return

        reader = EstacasTXTReader()
        resultado = reader.buscar_utm(obra, estaca)
        if resultado:
            easting, northing, zone = resultado
            self.edit_utm.setText(f"{zone}M {easting} {northing}")
            self.data_changed.emit()
        else:
            QMessageBox.information(self, "Não encontrado",
                                    f"Estaca '{estaca}' não encontrada para a obra '{obra}'.")

    def _on_converter_coordenada(self):
        dialog = CoordinateConverterDialog(self)
        if dialog.exec():
            if hasattr(dialog, 'result_utm'):
                self.edit_utm.setText(dialog.result_utm)
                self.data_changed.emit()

    def _on_ler_foto(self):
        self.ler_foto_requested.emit()

    def fill_from_metadata(self, meta: dict):
        if not meta:
            return

        obra = meta.get("obra", "").upper()
        idx = self.combo_obra.findText(obra)
        if idx >= 0:
            self.combo_obra.setCurrentIndex(idx)

        servico = meta.get("servico", "").upper()
        idx = self.combo_servico.findText(servico)
        if idx < 0:
            for i in range(self.combo_servico.count()):
                item_text = self.combo_servico.itemText(i).upper()
                if item_text in servico or servico in item_text:
                    idx = i
                    break
        if idx >= 0:
            self.combo_servico.setCurrentIndex(idx)

        self.edit_estaca.setText(meta.get("estaca", ""))

        lado = meta.get("lado", "").upper()
        idx = self.combo_lado.findText(lado)
        if idx >= 0:
            self.combo_lado.setCurrentIndex(idx)

        self.edit_utm.setText(meta.get("utm", ""))

        data = meta.get("data", "")
        partes = data.split("/")
        if len(partes) == 3:
            self.edit_dia.setText(partes[0])
            try:
                mes = int(partes[1]) - 1
                if 0 <= mes < 12:
                    self.combo_mes.setCurrentIndex(mes)
            except ValueError:
                pass
            self.edit_ano.setText(partes[2])

        self.data_changed.emit()

    def get_estaca_adjustment(self):
        return self.estaca_adjust.get_adjustment()

    def build_legend_text(self):
        linha_coord = self.edit_utm.text()
        
        estaca_original = self.edit_estaca.text()
        ajuste = self.get_estaca_adjustment()
        estaca_final = EstacaAdjuster.apply_adjustment_to_text(estaca_original, ajuste)
        
        if self.check_data.isChecked():
            linha_data = f"{self.edit_dia.text()}/{self.combo_mes.currentText()}/{self.edit_ano.text()}"
        else:
            linha_data = " "
        
        texto = (
            linha_coord + "\r"
            "BR-319/AM\r"
            f"{self.combo_obra.currentText()}\r"
            f"ESTACA: {estaca_final}\r"
            f"LADO: {self.combo_lado.currentText()}\r"
            f"SERVIÇO: {self.combo_servico.currentText()}\r"
            f"{linha_data}"
        )
        
        obs = self.edit_obs.toPlainText().strip()
        if obs:
            texto += "\r" + obs
        
        return texto

    def get_selected_font(self):
        return self.combo_fonte.currentText()