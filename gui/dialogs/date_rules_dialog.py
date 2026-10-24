from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QScrollArea, QWidget, QCheckBox, QLabel, QDialogButtonBox,
                               QDateEdit, QComboBox)
from PySide6.QtCore import Qt, QDate, Signal

class DateRuleWidget(QWidget):
    """Widget representando uma única regra de data com suporte a alterar ou omitir."""
    remove_requested = Signal(object)

    def __init__(self, original_date=None, action="alterar", new_date=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("De:"))
        self.original_date_edit = QDateEdit()
        self.original_date_edit.setCalendarPopup(True)
        self.original_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.original_date_edit.setDate(original_date if original_date else QDate.currentDate())
        layout.addWidget(self.original_date_edit)

        layout.addWidget(QLabel("Ação:"))
        self.combo_action = QComboBox()
        self.combo_action.addItems(["Alterar para", "Omitir data"])
        layout.addWidget(self.combo_action)

        self.new_date_edit = QDateEdit()
        self.new_date_edit.setCalendarPopup(True)
        self.new_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.new_date_edit.setDate(new_date if new_date else QDate.currentDate())
        layout.addWidget(self.new_date_edit)

        self.combo_action.currentTextChanged.connect(self._on_action_changed)
        
        # Configurar estado inicial
        if action == "omitir":
            self.combo_action.setCurrentIndex(1)
            self.new_date_edit.setVisible(False)
        else:
            self.combo_action.setCurrentIndex(0)
            self.new_date_edit.setVisible(True)

        self.btn_remove = QPushButton("−")
        self.btn_remove.setFixedWidth(30)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self.btn_remove)

    def _on_action_changed(self, text):
        is_alterar = (text == "Alterar para")
        self.new_date_edit.setVisible(is_alterar)

    def get_rule(self):
        orig = self.original_date_edit.date().toString("dd/MM/yyyy")
        action = "omitir" if self.combo_action.currentIndex() == 1 else "alterar"
        nova = self.new_date_edit.date().toString("dd/MM/yyyy")
        return {"original": orig, "action": action, "new": nova}


class DateRulesDialog(QDialog):
    """Diálogo isolado para gerenciar regras de data."""
    def __init__(self, parent=None, initial_rules=None, ignore_non_matching=True):
        super().__init__(parent)
        self.setWindowTitle("Configurar Regras de Data")
        self.resize(550, 400)
        
        self.rules_widgets = []
        
        layout = QVBoxLayout(self)
        
        # Scroll Area para as regras
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.rules_container = QVBoxLayout(self.scroll_content)
        self.rules_container.setSpacing(5)
        self.rules_container.addStretch() # Empurra itens para cima
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
        # Botões auxiliares
        btn_add = QPushButton("+ Adicionar Regra")
        btn_add.clicked.connect(self._on_add_rule)
        layout.addWidget(btn_add, alignment=Qt.AlignLeft)
        
        self.check_ignore = QCheckBox("Ignorar arquivos sem correspondência de data")
        self.check_ignore.setChecked(ignore_non_matching)
        layout.addWidget(self.check_ignore)
        
        # Botões de OK/Cancelar
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
        # Carregar regras iniciais
        if initial_rules:
            for rule in initial_rules:
                orig = QDate.fromString(rule.get('original', ''), "dd/MM/yyyy")
                action = rule.get('action', 'alterar')
                nova = QDate.fromString(rule.get('new', ''), "dd/MM/yyyy")
                self.add_rule_widget(orig, action, nova)
                
    def add_rule_widget(self, orig=None, action='alterar', nova=None):
        w = DateRuleWidget(orig, action, nova)
        w.remove_requested.connect(self._on_remove_rule)
        # insere antes do stretch item
        self.rules_container.insertWidget(self.rules_container.count() - 1, w)
        self.rules_widgets.append(w)
        
    def _on_add_rule(self):
        self.add_rule_widget()
        
    def _on_remove_rule(self, widget):
        if widget in self.rules_widgets:
            self.rules_widgets.remove(widget)
            self.rules_container.removeWidget(widget)
            widget.deleteLater()
            
    def get_settings(self):
        rules = [w.get_rule() for w in self.rules_widgets]
        return {
            'date_rules': rules,
            'ignore_non_matching': self.check_ignore.isChecked()
        }
