"""Update dialog for AutoLogin application."""

import webbrowser
from PyQt5 import QtWidgets, QtCore, QtGui
from typing import Optional
import threading

from autologin.utils.updater import download_update, apply_update, GITHUB_REPO


class UpdateAvailableDialog(QtWidgets.QDialog):
    """Dialog shown when an update is available."""
    
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        current_version: str,
        new_version: str,
        release_notes: str = "",
        download_url: Optional[str] = None
    ):
        super().__init__(parent)
        self.download_url = download_url
        self.setWindowTitle("Update Available")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header with icon
        header_layout = QtWidgets.QHBoxLayout()
        
        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(
            self.style().standardPixmap(QtWidgets.QStyle.SP_ArrowUp).scaled(48, 48)
        )
        header_layout.addWidget(icon_label)
        
        header_text = QtWidgets.QLabel(
            f"<h2>Update Available!</h2>"
            f"<p>A new version of AutoLogin is available.</p>"
            f"<p><b>Current Version:</b> {current_version}<br/>"
            f"<b>New Version:</b> {new_version}</p>"
        )
        header_text.setTextFormat(QtCore.Qt.RichText)
        header_text.setWordWrap(True)
        header_layout.addWidget(header_text, 1)
        
        layout.addLayout(header_layout)
        
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
        
        # Info about what will happen
        info_label = QtWidgets.QLabel(
            "<i>The update will be downloaded and the installer will launch. "
            "Please close this application before installing.</i>"
        )
        info_label.setTextFormat(QtCore.Qt.RichText)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.later_btn = QtWidgets.QPushButton("Remind Me Later")
        self.later_btn.clicked.connect(self.reject)
        
        if download_url:
            self.update_btn = QtWidgets.QPushButton("Download && Install")
            self.update_btn.setDefault(True)
            self.update_btn.clicked.connect(self.accept)
            self.update_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px; "
                "border-radius: 5px; font-weight: bold; font-size: 14px; }"
                "QPushButton:hover { background-color: #45a049; }"
            )
        else:
            self.update_btn = QtWidgets.QPushButton("Open Downloads Page")
            self.update_btn.setDefault(True)
            self.update_btn.clicked.connect(self._open_releases_page)
            self.update_btn.setStyleSheet(
                "QPushButton { background-color: #2196F3; color: white; padding: 10px 20px; "
                "border-radius: 5px; font-weight: bold; font-size: 14px; }"
                "QPushButton:hover { background-color: #1976D2; }"
            )
        
        button_layout.addWidget(self.later_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.update_btn)
        
        layout.addLayout(button_layout)
    
    def _open_releases_page(self):
        """Open the GitHub releases page in browser."""
        url = f"https://github.com/{GITHUB_REPO}/releases/latest"
        webbrowser.open(url)
        self.reject()


class UpdateProgressDialog(QtWidgets.QDialog):
    """Dialog showing download progress."""
    
    progress_updated = QtCore.pyqtSignal(int, int)
    download_complete = QtCore.pyqtSignal(str)
    download_failed = QtCore.pyqtSignal(str)
    
    def __init__(self, parent: Optional[QtWidgets.QWidget], download_url: str):
        super().__init__(parent)
        self.download_url = download_url
        self.setWindowTitle("Downloading Update")
        self.setMinimumWidth(450)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Icon and title
        header_layout = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(
            self.style().standardPixmap(QtWidgets.QStyle.SP_ArrowDown).scaled(32, 32)
        )
        header_layout.addWidget(icon_label)
        
        self.status_label = QtWidgets.QLabel("<b>Downloading update...</b>")
        self.status_label.setTextFormat(QtCore.Qt.RichText)
        header_layout.addWidget(self.status_label, 1)
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)
        
        # Size info
        self.size_label = QtWidgets.QLabel("Preparing download...")
        self.size_label.setStyleSheet("color: #666;")
        layout.addWidget(self.size_label)
        
        # Cancel button
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
            self.download_failed.emit("Failed to download update file. Please try again.")
    
    def _on_progress(self, downloaded: int, total: int):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            downloaded_mb = downloaded / 1024 / 1024
            total_mb = total / 1024 / 1024
            self.size_label.setText(
                f"{downloaded_mb:.1f} MB / {total_mb:.1f} MB ({percent}%)"
            )
        else:
            downloaded_mb = downloaded / 1024 / 1024
            self.size_label.setText(f"{downloaded_mb:.1f} MB downloaded")
    
    def _on_complete(self, path: str):
        self.status_label.setText("<b>Download complete!</b>")
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(False)
        self.size_label.setText("Launching installer...")
        
        # Apply the update
        if apply_update(self._download_path):
            QtWidgets.QMessageBox.information(
                self,
                "Update Ready",
                "The installer has been launched.\n\n"
                "Please close this application and follow the installer instructions "
                "to complete the update."
            )
            self.accept()
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Update Downloaded",
                f"The update has been downloaded to:\n{path}\n\n"
                "Please close this application and run the installer manually."
            )
            self.accept()
    
    def _on_failed(self, error: str):
        self.status_label.setText("<b>Download failed</b>")
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
        self.setText("You're up to date!")
        self.setInformativeText(
            f"AutoLogin version {current_version} is the latest version available."
        )
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)


class CheckingUpdateDialog(QtWidgets.QDialog):
    """Small dialog shown while checking for updates."""
    
    def __init__(self, parent: Optional[QtWidgets.QWidget]):
        super().__init__(parent)
        self.setWindowTitle("Checking for Updates")
        self.setFixedSize(300, 100)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Spinner/progress
        self.label = QtWidgets.QLabel("Checking for updates...")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
