from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox
from core.utm_converter import UTMConverter

class CoordinateConverterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Converter Coordenada")
        self.result_utm = None

        layout = QFormLayout(self)
        self.edit_lat = QLineEdit()
        self.edit_lon = QLineEdit()
        layout.addRow("Latitude:", self.edit_lat)
        layout.addRow("Longitude:", self.edit_lon)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(self.buttons)
        self.buttons.accepted.connect(self._on_ok)
        self.buttons.rejected.connect(self.reject)

    def _on_ok(self):
        try:
            lat = float(self.edit_lat.text().replace(',', '.'))
            lon = float(self.edit_lon.text().replace(',', '.'))
            easting, northing, zone = UTMConverter.lat_lon_to_utm(lat, lon)
            self.result_utm = UTMConverter.format_utm(easting, northing, zone)
            self.accept()
        except ValueError:
            QMessageBox.warning(self, "Erro", "Digite números válidos para latitude e longitude.")