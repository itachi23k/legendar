import math

class UTMConverter:
    """Converte coordenadas geográficas (WGS84) para UTM."""

    @staticmethod
    def lat_lon_to_utm(lat, lon):
        """Retorna (easting, northing, zone)."""
        zone = int(math.floor((lon + 180) / 6)) + 1
        is_south = lat < 0
        
        a = 6378137.0
        b = 6356752.3142
        e = math.sqrt(1 - (b / a) ** 2)
        
        lat_abs = abs(lat) * math.pi / 180
        lon_rad = lon * math.pi / 180
        lon0 = ((zone - 1) * 6 - 180 + 3) * math.pi / 180

        N = a / math.sqrt(1 - (e * math.sin(lat_abs)) ** 2)
        T = math.tan(lat_abs) ** 2
        C = (e ** 2 * math.cos(lat_abs) ** 2) / (1 - e ** 2)
        A = (lon_rad - lon0) * math.cos(lat_abs)

        M = a * ((1 - e ** 2 / 4 - 3 * e ** 4 / 64 - 5 * e ** 6 / 256) * lat_abs
                 - (3 * e ** 2 / 8 + 3 * e ** 4 / 32 + 45 * e ** 6 / 1024) * math.sin(2 * lat_abs)
                 + (15 * e ** 4 / 256 + 45 * e ** 6 / 1024) * math.sin(4 * lat_abs)
                 - (35 * e ** 6 / 3072) * math.sin(6 * lat_abs))

        k0 = 0.9996
        x = k0 * N * (A + (1 - T + C) * A ** 3 / 6
                      + (5 - 18 * T + T ** 2 + 72 * C - 58 * e ** 2 / (1 - e ** 2)) * A ** 5 / 120) + 500000
        y = k0 * (M + N * math.tan(lat_abs) * (A ** 2 / 2
                                                + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24
                                                + (61 - 58 * T + T ** 2 + 600 * C - 330 * e ** 2 / (1 - e ** 2)) * A ** 6 / 720))
        
        if is_south:
            y = 10000000 - y
        
        return int(round(x)), int(round(y)), zone

    @staticmethod
    def format_utm(easting, northing, zone):
        """Formata como string: '20M 123456 7654321'."""
        hemisphere = "M" if northing >= 0 else "S"
        return f"{zone}{hemisphere} {easting} {northing}"