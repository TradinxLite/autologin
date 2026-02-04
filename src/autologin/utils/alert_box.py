# from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon


def fail_box_alert(title, message, details=None):
    m = QMessageBox()
    m.setIcon(QMessageBox.Critical)
    m.setWindowTitle(title)
    m.setText(message if len(message) < 200 else message[:200] + " …")
    if details:
        m.setDetailedText(details)  # stack trace here; doesn’t inflate main dialog
    m.setStandardButtons(QMessageBox.Ok)
    m.setMinimumWidth(420)
    m.exec_()


def ok_box_alert(title, message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(message)
    msg.setWindowTitle(title)
    # msg.setWindowIcon(QIcon("assets/logo.jpg"))
    msg.setStandardButtons(QMessageBox.Ok)
    # QTimer.singleShot(2500, msg.close)
    msg.exec_()