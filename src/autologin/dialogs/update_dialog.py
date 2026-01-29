"""Update dialog for AutoLogin application."""

from PyQt5 import QtWidgets, QtCore, QtGui
from typing import Optional
import threading

from autologin.utils.updater import download_update, apply_update


class UpdateAvailableDialog(QtWidgets.QDialog):
    """Dialog shown when an update is available."""
    
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        current_version: str,
        new_version: str,
        release_notes: str = ""
    ):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.setMinimumWidth(450)
        self.setModal(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header
        header = QtWidgets.QLabel(
            f"<h2>🎉 A new version is available!</h2>"
            f"<p>Version <b>{new_version}</b> is now available. "
            f"You are currently using version <b>{current_version}</b>.</p>"
        )
        header.setTextFormat(QtCore.Qt.RichText)
        header.setWordWrap(True)
        layout.addWidget(header)
        
        # Release notes
        if release_notes:
            notes_group = QtWidgets.QGroupBox("What's New")
            notes_layout = QtWidgets.QVBoxLayout(notes_group)
            notes_text = QtWidgets.QTextEdit()
            notes_text.setReadOnly(True)
            notes_text.setPlainText(release_notes)
            notes_text.setMaximumHeight(200)
            notes_layout.addWidget(notes_text)
            layout.addWidget(notes_group)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.skip_btn = QtWidgets.QPushButton("Skip This Version")
        self.skip_btn.clicked.connect(self.reject)
        
        self.later_btn = QtWidgets.QPushButton("Remind Me Later")
        self.later_btn.clicked.connect(self.reject)
        
        self.update_btn = QtWidgets.QPushButton("Download Update")
        self.update_btn.setDefault(True)
        self.update_btn.clicked.connect(self.accept)
        self.update_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        
        button_layout.addWidget(self.skip_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.later_btn)
        button_layout.addWidget(self.update_btn)
        
        layout.addLayout(button_layout)


class UpdateProgressDialog(QtWidgets.QDialog):
    """Dialog showing download progress."""
    
    progress_updated = QtCore.pyqtSignal(int, int)
    download_complete = QtCore.pyqtSignal(str)
    download_failed = QtCore.pyqtSignal(str)
    
    def __init__(self, parent: Optional[QtWidgets.QWidget], download_url: str):
        super().__init__(parent)
        self.download_url = download_url
        self.setWindowTitle("Downloading Update")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        self.status_label = QtWidgets.QLabel("Downloading update...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        self.size_label = QtWidgets.QLabel("")
        layout.addWidget(self.size_label)
        
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_btn, alignment=QtCore.Qt.AlignCenter)
        
        # Connect signals
        self.progress_updated.connect(self._on_progress)
        self.download_complete.connect(self._on_complete)
        self.download_failed.connect(self._on_failed)
        
        self._cancelled = False
        self._download_path = None
    
    def start_download(self):
        """Start the download in a background thread."""
        thread = threading.Thread(target=self._download_worker, daemon=True)
        thread.start()
    
    def _download_worker(self):
        """Background worker for downloading."""
        def progress_callback(downloaded, total):
            if not self._cancelled:
                self.progress_updated.emit(downloaded, total)
        
        path = download_update(self.download_url, progress_callback)
        
        if self._cancelled:
            return
        
        if path:
            self._download_path = path
            self.download_complete.emit(str(path))
        else:
            self.download_failed.emit("Failed to download update file")
    
    def _on_progress(self, downloaded: int, total: int):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            self.size_label.setText(
                f"{downloaded / 1024 / 1024:.1f} MB / {total / 1024 / 1024:.1f} MB"
            )
        else:
            self.size_label.setText(f"{downloaded / 1024 / 1024:.1f} MB downloaded")
    
    def _on_complete(self, path: str):
        self.status_label.setText("Download complete! Installing...")
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(False)
        
        # Apply the update
        if apply_update(self._download_path):
            QtWidgets.QMessageBox.information(
                self,
                "Update Ready",
                "The update has been downloaded. Please follow the installer instructions "
                "to complete the update. The application will now close."
            )
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Update",
                f"Update downloaded to:\n{path}\n\nPlease install it manually."
            )
            self.accept()
    
    def _on_failed(self, error: str):
        self.status_label.setText(f"Download failed")
        QtWidgets.QMessageBox.critical(self, "Download Failed", error)
        self.reject()
    
    def _on_cancel(self):
        self._cancelled = True
        self.reject()


class NoUpdateDialog(QtWidgets.QMessageBox):
    """Dialog shown when no update is available."""
    
    def __init__(self, parent: Optional[QtWidgets.QWidget], current_version: str):
        super().__init__(parent)
        self.setWindowTitle("Check for Updates")
        self.setIcon(QtWidgets.QMessageBox.Information)
        self.setText(f"You're up to date!")
        self.setInformativeText(
            f"AutoLogin {current_version} is currently the newest version available."
        )
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)
