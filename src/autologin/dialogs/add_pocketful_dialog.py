from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
import os


class AddPocketfulAccountDialog(QDialog):
    def __init__(self):
        super(AddPocketfulAccountDialog, self).__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "pocketful_dialog.ui"), self)
        self.setWindowTitle("Add Pocketful Account")

    def get_inputs(self):
        return {
            "client_id": self.client_id_line.text(),
            "password": self.password_line.text()
        }

    def set_inputs(self, data: dict):
        self.client_id_line.setText(data.get("client_id", ""))
        self.password_line.setText(data.get("password", ""))

