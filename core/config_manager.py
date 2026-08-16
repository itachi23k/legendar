import json
from pathlib import Path

class ConfigManager:
    """Gerencia persistência de configurações em arquivo JSON."""

    DEFAULT_CONFIG = {
        "obra_idx": 0,
        "servico_idx": 0,
        "last_utm": "20M 000000 0000000",
        "estaca": "0",
        "lado": "D",
        "dia": "04",
        "mes_idx": 0,
        "ano": "2026",
        "show_date": True,
        "obs": "",
        "font": "Araboto-Normal",
        "last_lat": "",
        "last_lon": "",
        "batch_preferences": None
    }

    def __init__(self, file_path="config.json"):
        self.file_path = Path(file_path)
        self.config = self.load()

    def load(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Garante que todas as chaves padrão existam
                    for key, value in self.DEFAULT_CONFIG.items():
                        if key not in loaded:
                            loaded[key] = value
                    return loaded
            except:
                pass
        return self.DEFAULT_CONFIG.copy()

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except:
            pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()