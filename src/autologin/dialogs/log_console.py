
import sys
import logging
from PyQt5 import QtWidgets, QtGui, QtCore

class LogStream(QtCore.QObject):
    """Stream object that emits signals when written to."""
    messageWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        if text:
            self.messageWritten.emit(str(text))
    
    def flush(self):
        pass

class LogConsole(QtWidgets.QDialog):
    """
    A separate window to display application logs and stdout/stderr.
    Useful for debugging in production (packaged apps).
    """
    # Define signal for thread-safe logging from handler
    new_log_record = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Logs")
        self.resize(800, 600)
        
        # Connect signals
        self.new_log_record.connect(self.append_log_record)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Log display area
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        font = QtGui.QFont("Monospace")
        font.setStyleHint(QtGui.QFont.Monospace)
        self.text_edit.setFont(font)
        layout.addWidget(self.text_edit)
        
        # Controls
        btn_layout = QtWidgets.QHBoxLayout()
        
        self.level_combo = QtWidgets.QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self._update_filter)
        btn_layout.addWidget(QtWidgets.QLabel("Min Level:"))
        btn_layout.addWidget(self.level_combo)
        
        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.clicked.connect(self.text_edit.clear)
        btn_layout.addWidget(self.clear_btn)
        
        self.save_btn = QtWidgets.QPushButton("Save to File")
        self.save_btn.clicked.connect(self._save_logs)
        btn_layout.addWidget(self.save_btn)
        
        # Auto-scroll checkbox
        self.autoscroll_check = QtWidgets.QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        btn_layout.addWidget(self.autoscroll_check)
        
        btn_layout.addStretch()
        
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        # Configure logging
        # Force root logger to DEBUG so we catch everything, then filter in the handler
        logging.getLogger().setLevel(logging.DEBUG)
        
        self.handler = QtLogHandler(self)
        self.handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))
        logging.getLogger().addHandler(self.handler)
        
        # Redirect stdout/stderr
        self.stdout_stream = LogStream()
        self.stdout_stream.messageWritten.connect(self.append_stdout)
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_stream

        self.stderr_stream = LogStream()
        self.stderr_stream.messageWritten.connect(self.append_stderr)
        self.original_stderr = sys.stderr
        sys.stderr = self.stderr_stream

    def _update_filter(self, text):
        level = getattr(logging, text)
        self.handler.setLevel(level)
        
    def _save_logs(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Logs", "autologin_logs.txt", "Text Files (*.txt)"
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.text_edit.toPlainText())

    def append_log_record(self, record):
        """Slot to append log record."""
        msg = self.handler.format(record)
        # Color coding for logs
        color = "#000000"  # Black
        if record.levelno >= logging.ERROR:
            color = "#FF0000"  # Red
        elif record.levelno >= logging.WARNING:
            color = "#FF8C00"  # Orange
        elif record.levelno == logging.DEBUG:
            color = "#808080"  # Gray
        
        html = f'<span style="color:{color}">{msg}</span>'
        self.text_edit.append(html)
        self._check_scroll()

    def append_stdout(self, text):
        """Slot for stdout text."""
        # Clean up newlines for HTML
        text = text.replace("\n", "<br>")
        html = f'<span style="color:#000080">{text}</span>'  # Navy blue for stdout
        self.text_edit.insertHtml(html)
        self._check_scroll()

    def append_stderr(self, text):
        """Slot for stderr text."""
        text = text.replace("\n", "<br>")
        html = f'<span style="color:#8B0000">{text}</span>'  # Dark red for stderr
        self.text_edit.insertHtml(html)
        self._check_scroll()
        
    def _check_scroll(self):
        if self.autoscroll_check.isChecked():
            self.text_edit.moveCursor(QtGui.QTextCursor.End)
    
    def closeEvent(self, event):
        # Don't destroy usage of handler, just hide window
        self.hide()
        event.ignore()
        
    def __del__(self):
        # Restore stdout/stderr if destroyed
        if hasattr(self, 'original_stdout'):
            sys.stdout = self.original_stdout
        if hasattr(self, 'original_stderr'):
            sys.stderr = self.original_stderr

class QtLogHandler(logging.Handler):
    """Log handler that emits a signal to the Qt widget."""
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        
    def emit(self, record):
        # Emit signal to update GUI on main thread
        try:
            self.widget.new_log_record.emit(record)
        except Exception:
            pass
