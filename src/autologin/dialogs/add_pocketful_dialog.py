from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QDialogButtonBox
from PyQt5.QtCore import Qt

class AddPocketfulAccountDialog(QDialog):
    def __init__(self):
        super(AddPocketfulAccountDialog, self).__init__()
        self.setWindowTitle("Add Pocketful Account")
        self.resize(280, 208)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        
        # Grid layout for fields
        self.grid_layout = QGridLayout()
        
        # Client ID
        self.grid_layout.addWidget(QLabel("Client ID"), 0, 0)
        self.client_id_line = QLineEdit()
        self.grid_layout.addWidget(self.client_id_line, 0, 1)
        
        # Password
        self.grid_layout.addWidget(QLabel("Password"), 1, 0)
        self.password_line = QLineEdit()
        self.grid_layout.addWidget(self.password_line, 1, 1)
        
        # PIN (mapped to MPIN)
        self.grid_layout.addWidget(QLabel("PIN (MPIN)"), 2, 0)
        self.mpin_line = QLineEdit()
        self.grid_layout.addWidget(self.mpin_line, 2, 1)
        
        self.layout.addLayout(self.grid_layout)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        
        # Tab order
        self.setTabOrder(self.client_id_line, self.password_line)
        self.setTabOrder(self.password_line, self.mpin_line)
        self.setTabOrder(self.mpin_line, self.button_box)

    def get_inputs(self):
        return {
            "client_id": self.client_id_line.text(),
            "password": self.password_line.text(),
            "mpin": self.mpin_line.text()
        }

    def set_inputs(self, data: dict):
        self.client_id_line.setText(data.get("client_id", ""))
        self.password_line.setText(data.get("password", ""))
        self.mpin_line.setText(data.get("mpin", ""))

