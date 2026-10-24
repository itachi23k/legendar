from PySide6.QtWidgets import QListWidget, QAbstractItemView
from pathlib import Path

class ImageListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.current_filter = "TODOS"

    def add_files(self, files):
        for f in files:
            self.addItem(f)
        self.apply_current_filter()

    def get_files(self, visible_only=True):
        files = []
        for i in range(self.count()):
            item = self.item(i)
            if not visible_only or not item.isHidden():
                files.append(item.text())
        return files

    def set_filter(self, filter_type):
        self.current_filter = filter_type
        for i in range(self.count()):
            item = self.item(i)
            file_path = item.text()
            file_name = Path(file_path).name.upper()
            
            show = True
            if filter_type == "TODOS":
                show = True
            elif filter_type == "LEGEND":
                # Contém sufixos indicando que foi legendado/modificado
                show = any(suffix in file_name for suffix in ["_LEGENDADO", "_MODED", "_LOTE", "_REG", "_IND"])
            elif filter_type == "SINGLE":
                # Contém sufixos do modo individual
                show = any(suffix in file_name for suffix in ["_IND", "_INDIV"])
            elif filter_type == "DATA":
                # Contém data (não contém a abreviação de Sem Data: SD ou ND)
                show = not any(suffix in file_name for suffix in ["_SD", "_ND"])
            elif filter_type == "SEM DATA":
                # Omitiu a data (contém SD ou ND no sufixo)
                show = any(suffix in file_name for suffix in ["_SD", "_ND"])
            elif filter_type == "LOTE":
                # Contém sufixos do modo lote
                show = any(suffix in file_name for suffix in ["_LOTE", "_MODED", "_REG"])
            elif filter_type == "CLEAN":
                # Contém CLEAN no nome do arquivo (originais)
                show = "CLEAN" in file_name
            elif filter_type == "ROT":
                # Contém _ROT no nome do arquivo (correção de câmera)
                show = "_ROT" in file_name
            else:
                show = True
                
            item.setHidden(not show)

    def apply_current_filter(self):
        self.set_filter(self.current_filter)

    def clear(self):
        super().clear()