from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
import os


class AddUpstoxAccountDialog(QDialog):
    def __init__(self, call_back_fn):
        super(AddUpstoxAccountDialog, self).__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "upstox_dialog.ui"), self)
        self.setWindowTitle("Add Upstox Account")
        self.how_to_button.clicked.connect(call_back_fn)


    def get_inputs(self):
        return {
            "client_id": self.client_id_line.text(),
            "mobile_number": self.mobile_no_line.text(),
            "totp_key": self.totp_key_line.text(),
            "mpin": self.mpin_line.text(),
            "api_key": self.api_key_line.text(),
        }
    
    def set_inputs(self, data: dict):
        self.client_id_line.setText(data.get("client_id", ""))
        self.mpin_line.setText(data.get("mpin", ""))
        self.mobile_no_line.setText(data.get("mobile_number", ""))
        self.totp_key_line.setText(data.get("totp_key", ""))
        self.api_key_line.setText(data.get("api_key", ""))