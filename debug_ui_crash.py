import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5 import uic

def test_ui_loading():
    app = QApplication(sys.argv)
    
    current_directory = os.getcwd()
    ui_path = os.path.join(current_directory, "src", "autologin", "ui", "pocketful_dialog.ui")
    print(f"Attempting to load UI from: {ui_path}")
    
    if not os.path.exists(ui_path):
        print("Error: UI file not found!")
        return

    try:
        dialog = QDialog()
        uic.loadUi(ui_path, dialog)
        print("Success! UI loaded perfectly.")
    except Exception as e:
        print(f"Caught exception loading UI: {e}")

if __name__ == "__main__":
    test_ui_loading()
