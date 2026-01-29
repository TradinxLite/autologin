from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
import os


class AddKotakNeoAccountDialog(QDialog):
    def __init__(self, call_back_fn):
        super(AddKotakNeoAccountDialog, self).__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "kotakneo_dialog.ui"), self)
        self.setWindowTitle("Add KotakNeo Account")
        self.how_to_button.clicked.connect(call_back_fn)

    def get_inputs(self):
        return {
            "client_id": self.client_id_line.text(),
            "mpin": self.mpin_line.text(),
            "totp_key": self.totp_key_line.text(),
            "mobile_number": self.mobile_number_line.text()
        }
    
    def set_inputs(self, data: dict):
        self.client_id_line.setText(data.get("client_id", ""))
        self.mpin_line.setText(data.get("mpin", ""))
        self.totp_key_line.setText(data.get("totp_key", ""))
        self.mobile_number_line.setText(data.get("mobile_number", ""))
    
 