from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
import os

class AddMotilalOswalAccountDialog(QDialog):
    def __init__(self, call_back_fn):
        super(AddMotilalOswalAccountDialog, self).__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "motilaloswal_dialog.ui"), self)
        self.setWindowTitle("Add Motilal Oswal Account")
        self.how_to_button.clicked.connect(call_back_fn)


    def get_inputs(self):
        return {
            "client_id": self.client_id_line.text(),
            "password": self.password_line.text(),
            "totp_key": self.totp_key_line.text(),
            "api_key": self.api_key_line.text(),
            "dob" : self.two_fa_line.text()
        }
    
    def set_inputs(self, data: dict):
        self.client_id_line.setText(data.get("client_id", ""))
        self.password_line.setText(data.get("password", ""))
        self.totp_key_line.setText(data.get("totp_key", ""))
        self.api_key_line.setText(data.get("api_key", ""))
        self.two_fa_line.setText(data.get("dob", ""))