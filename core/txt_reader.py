from pathlib import Path
from core.utm_converter import UTMConverter

class EstacasTXTReader:
    """Busca coordenadas UTM no arquivo de estacas."""

    def __init__(self, file_path="C:\\estacas_cheias.txt"):
        self.file_path = Path(file_path)

    def buscar_utm(self, obra, estaca):
        """Retorna (easting, northing, zone) se encontrar."""
        if not self.file_path.exists():
            return None

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().replace('"', '')
                    if not line:
                        continue
                    cols = line.split(';')
                    if len(cols) >= 4 and cols[0].strip() == estaca and cols[1].strip() == obra:
                        try:
                            lat = float(cols[2].replace(',', '.'))
                            lon = float(cols[3].replace(',', '.'))
                            return UTMConverter.lat_lon_to_utm(lat, lon)
                        except ValueError:
                            return None
        except:
            pass
        return None