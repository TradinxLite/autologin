from PyQt5.QtWidgets import QDialog, QLabel, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5 import uic
import os
import webbrowser


class HowToAddZerodhaDialog(QDialog):
    def __init__(self):
        super().__init__()
        current_directory = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(current_directory, "..", "ui", "how_to_add_zerodha.ui"), self)
        self.setWindowTitle("How To Generate Zerodha TOTP Key")

        self.current_step_index = 0
        self.steps = [
            ("Step 1: Head over to https://kite.zerodha.com/", "zerodha_profile.png"),
            ("Step 2: Login with your credentials", "zerodha_profile.png"),
            ("Step 3: Go to your profile by clicking on your Client ID on the top right of the screen", "zerodha_profile.png"),
            ("Step 4: On the Profile Page, Click on External 2FA TOTP in the sidebar", "zerodha_generate_totp.png"),
            ("Step 6: Verify using the otp sent to your registered email", "zerodha_verify.png"),
            ("Step 7: Copy the TOTP key by clicking on the text below the QR Code, Scan the QR Code using your authenticator app. Enable your "
            "TOTP using your newly generated TOTP on your authenticator app and account Password", "zerodha_copy_totp.png"),
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
            self.stepLabel.linkActivated.connect(self.handle_link_click)
        else:
            self.stepLabel.setText(step_text)
        image_path = os.path.join(self.current_directory, "..", "resources", "images", image_file)
        self.imageLabel.setPixmap(QPixmap(image_path))

        self.prevButton.setEnabled(self.current_step_index > 0)
        self.nextButton.setEnabled(True)

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
        url = url.split("http", 1)[1]
        webbrowser.open("http" + url)