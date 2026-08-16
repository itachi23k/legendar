from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSpinBox
from PySide6.QtCore import Signal

class EstacaAdjustWidget(QWidget):
    """Widget para ajuste de estaca."""
    adjustment_changed = Signal(int)

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel("Ajuste Estaca:"))
        
        self.btn_decrement = QPushButton("-")
        self.btn_decrement.setFixedWidth(40)
        self.btn_decrement.setFixedHeight(30)
        
        self.spin_adjust = QSpinBox()
        self.spin_adjust.setRange(-9999, 9999)
        self.spin_adjust.setValue(0)
        self.spin_adjust.setSuffix(" m")
        self.spin_adjust.setFixedWidth(100)
        
        self.btn_increment = QPushButton("+")
        self.btn_increment.setFixedWidth(40)
        self.btn_increment.setFixedHeight(30)
        
        layout.addWidget(self.btn_decrement)
        layout.addWidget(self.spin_adjust)
        layout.addWidget(self.btn_increment)
        layout.addStretch()
        
        self.btn_decrement.clicked.connect(self._on_decrement)
        self.btn_increment.clicked.connect(self._on_increment)
        self.spin_adjust.valueChanged.connect(self._on_value_changed)
    
    def _on_decrement(self):
        self.spin_adjust.setValue(self.spin_adjust.value() - 5)
    
    def _on_increment(self):
        self.spin_adjust.setValue(self.spin_adjust.value() + 5)
    
    def _on_value_changed(self, value):
        self.adjustment_changed.emit(value)
    
    def get_adjustment(self):
        return self.spin_adjust.value()
    
    def set_adjustment(self, value):
        self.spin_adjust.setValue(value)