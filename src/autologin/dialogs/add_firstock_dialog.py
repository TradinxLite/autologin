from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
import os


class AddFirstockAccountDialog(QDialog):
    def __init__(self, call_back_fn):
        super(AddFirstockAccountDialog, self).__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "firstock_dialog.ui"), self)
        self.setWindowTitle("Add Firstock Account")
        self.how_to_button.clicked.connect(call_back_fn)

    def get_inputs(self):
        return {
            "client_id": self.client_id_line.text(),
            "password": self.password_line.text(),
            "totp_key": self.totp_key_line.text()
        }
    
    def set_inputs(self, data: dict):
        self.client_id_line.setText(data.get("client_id", ""))
        self.password_line.setText(data.get("password", ""))
        self.totp_key_line.setText(data.get("totp_key", ""))
    
 