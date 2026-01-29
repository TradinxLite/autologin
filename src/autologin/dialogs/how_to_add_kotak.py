import os
import webbrowser
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton
from PyQt5.QtGui import QPixmap


class HowToAddKotakNeoDialog(QDialog):
    def __init__(self):
        super().__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "how_to_add_kotak.ui"), self)
        self.setWindowTitle("How To Generate KotakNeo TOTP Key")

        self.current_step_index = 0
        self.steps = [
            ("Step 1: Head over to https://www.kotaksecurities.com/platform/kotak-neo-trade-api/totp-registration/", "kotak_site.png"),
            ("Step 2: Add your mobile number under Register totp section and verify using the received otp on your mobile number", "kotak_otp.png"),
            ("Step 3: Select the account in which you want to generate your totp", "kotak_select_account.png"),
            ("Step 4: Copy the TOTP key by clicking on the text below the QR code, save it in notepad and Enable the TOTP by scanning it using your authenticator app and using the first 6-digit TOTP", "kotak_totp.png"),
            ("Step 5: Click on continue and your totp has been successfully generated", "kotak_success.png"),
        ]

        self.stepLabel = self.findChild(QLabel, "stepLabel")
        self.imageLabel = self.findChild(QLabel, "imageLabel")
        self.nextButton = self.findChild(QPushButton, "nextButton")
        self.prevButton = self.findChild(QPushButton, "prevButton")

        self.nextButton.clicked.connect(self.next_step)
        self.prevButton.clicked.connect(self.prev_step)

        self.current_directory = current_directory
        self.show_step()

    def show_step(self):
        step_text, image_file = self.steps[self.current_step_index]
        if "http" in step_text:
            url = step_text.split("http", 1)[1]
            prefix = step_text.split("http", 1)[0]
            self.stepLabel.setText(f"{prefix}<a href='http{url}'>http{url}</a>")
            self.stepLabel.setOpenExternalLinks(False)
            try:
                self.stepLabel.linkActivated.disconnect()
            except TypeError:
                pass
            self.stepLabel.linkActivated.connect(self.handle_link_click)
        else:
            self.stepLabel.setText(step_text)

        image_path = os.path.join(self.current_directory, "..", "resources", "images", image_file)
        if os.path.exists(image_path):
            self.imageLabel.setPixmap(QPixmap(image_path))
        else:
            self.imageLabel.setText("Image not found.")

        self.prevButton.setEnabled(self.current_step_index > 0)
        self.nextButton.setEnabled(True)

        if self.current_step_index == len(self.steps) - 1:
            self.nextButton.setText("Finish")
        else:
            self.nextButton.setText("Next >")

    def next_step(self):
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.show_step()
        else:
            self.accept()

    def prev_step(self):
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self.show_step()

    def handle_link_click(self, url):
        webbrowser.open(url)