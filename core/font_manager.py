import os
from pathlib import Path
from PySide6.QtGui import QFontDatabase, QFont

class FontManager:
    """Gerencia o carregamento e disponibilização da fonte Araboto-Normal."""

    FONT_PATHS = [
        "Araboto-Normal.ttf",
        "Araboto Normal.ttf",
        "araboto-normal.ttf",
        "fonts/Araboto-Normal.ttf",
        "assets/fonts/Araboto-Normal.ttf",
        str(Path.home() / "Fonts/Araboto-Normal.ttf"),
        str(Path.home() / "fonts/Araboto-Normal.ttf"),
        "C:/Windows/Fonts/Araboto-Normal.ttf",
        "C:/Windows/Fonts/Araboto.ttf",
    ]

    @classmethod
    def load_araboto_font(cls):
        """Tenta carregar a fonte Araboto-Normal."""
        font_db = QFontDatabase()
        families = font_db.families()

        # Procurar por variações do nome
        for family in families:
            if "araboto" in family.lower():
                return family

        # Tentar carregar de arquivo
        for font_path in cls.FONT_PATHS:
            if os.path.exists(font_path):
                try:
                    font_id = QFontDatabase.addApplicationFont(font_path)
                    if font_id != -1:
                        loaded_families = QFontDatabase.applicationFontFamilies(font_id)
                        if loaded_families:
                            return loaded_families[0]
                except:
                    pass

        # Fallback
        if "Arial" in families:
            return "Arial"
        elif families:
            return families[0]
        return "Arial"

    @classmethod
    def get_araboto_font(cls, size_pixels):
        """Retorna um objeto QFont configurado com Araboto-Normal."""
        family = cls.load_araboto_font()
        font = QFont(family)
        font.setPixelSize(int(size_pixels))
        font.setHintingPreference(QFont.PreferFullHinting)
        font.setStyleStrategy(QFont.PreferAntialias)
        return font