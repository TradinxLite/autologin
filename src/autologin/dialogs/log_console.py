
import logging
from PyQt5 import QtWidgets, QtGui, QtCore

class LogConsole(QtWidgets.QDialog):
    """
    A separate window to display application logs.
    Useful for debugging in production (packaged apps).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Logs")
        self.resize(800, 600)
        
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
        
        # Setup logging handler
        self.handler = QtLogHandler(self)
        self.handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))
        logging.getLogger().addHandler(self.handler)
        
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

    def append_log(self, record):
        msg = self.handler.format(record)
        
        # Color coding
        color = "#000000"  # Black
        if record.levelno >= logging.ERROR:
            color = "#FF0000"  # Red
        elif record.levelno >= logging.WARNING:
            color = "#FF8C00"  # Orange
        elif record.levelno == logging.DEBUG:
            color = "#808080"  # Gray
            
        html = f'<span style="color:{color}">{msg}</span>'
        self.text_edit.append(html)
        
        if self.autoscroll_check.isChecked():
            self.text_edit.moveCursor(QtGui.QTextCursor.End)


class QtLogHandler(logging.Handler):
    """Log handler that emits a signal/queues logs to the Qt widget."""
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        
    def emit(self, record):
        # We need to be thread-safe here if logs come from worker threads
        # Using QTimer.singleShot to execute on main thread is one way,
        # or signals. Here we trust Qt's thread safety for append? 
        # No, logs from threads MUST use signals.
        
        # Since we are inside the handler, effectively we can jus call a method on the widget
        # but we must ensure it runs on the GUI thread.
        QtCore.QMetaObject.invokeMethod(
            self.widget, 
            "append_log", 
            QtCore.Qt.QueuedConnection, 
            QtCore.Q_ARG(object, record)
        )
