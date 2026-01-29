from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
import os


class AddFivePaisaAccountDialog(QDialog):
    def __init__(self, call_back_fn):
        super(AddFivePaisaAccountDialog, self).__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "five_paisa_dialog.ui"), self)
        self.setWindowTitle("Add Five Paisa Account")
        self.how_to_button.clicked.connect(call_back_fn)

    def get_inputs(self):
        return {
            "client_id": self.client_id_line.text(),
            "mpin": self.mpin_line.text(),
            "totp_key": self.totp_key_line.text(),
        }
    
    def set_inputs(self, data: dict):
        self.client_id_line.setText(data.get("client_id", ""))
        self.mpin_line.setText(data.get("mpin", ""))
        self.totp_key_line.setText(data.get("totp_key", ""))
    
 