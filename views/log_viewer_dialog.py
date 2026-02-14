"""
Log viewer dialog for displaying application logs.
Provides read-only log display with auto-scroll and clear functionality.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QCheckBox, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from utils.app_logger import get_logger


class LogViewerDialog(QDialog):
    """Dialog for viewing application logs"""

    def __init__(self, parent=None):
        """
        Initialize log viewer dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = get_logger()
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self._refresh_log)

        self._create_ui()
        self._load_log()

    def _create_ui(self) -> None:
        """Create the user interface"""
        self.setWindowTitle("Debug Log")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header with controls
        header_layout = QHBoxLayout()

        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        header_layout.addWidget(self.auto_scroll_checkbox)

        # Auto-refresh checkbox
        self.auto_refresh_checkbox = QCheckBox("Auto-refresh (1s)")
        self.auto_refresh_checkbox.toggled.connect(self._on_auto_refresh_toggled)
        header_layout.addWidget(self.auto_refresh_checkbox)

        header_layout.addStretch()

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_log)
        header_layout.addWidget(self.refresh_button)

        # Clear button
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self._clear_log)
        header_layout.addWidget(self.clear_button)

        layout.addLayout(header_layout)

        # Log file path label
        log_path = self.logger.get_log_file_path()
        if log_path:
            self.path_label = QLabel(f"📄 {log_path}")
            self.path_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(self.path_label)

        # Log text display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Use monospace font for better log readability
        font = QFont("Courier New", 10)
        self.log_text.setFont(font)

        layout.addWidget(self.log_text)

        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

    def _load_log(self) -> None:
        """Load log content from file"""
        log_content = self.logger.read_log()
        self.log_text.setPlainText(log_content)

        # Auto-scroll to bottom if enabled
        if self.auto_scroll_checkbox.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        # Update status
        line_count = len(log_content.splitlines())
        self.status_label.setText(f"Lines: {line_count}")

    def _refresh_log(self) -> None:
        """Refresh log content"""
        self._load_log()

    def _clear_log(self) -> None:
        """Clear log file and display"""
        self.logger.clear_log()
        self.log_text.clear()
        self.status_label.setText("Log cleared")

    def _on_auto_refresh_toggled(self, checked: bool) -> None:
        """Handle auto-refresh toggle"""
        if checked:
            self.auto_refresh_timer.start(1000)  # Refresh every 1 second
        else:
            self.auto_refresh_timer.stop()

    def closeEvent(self, event) -> None:
        """Handle dialog close event"""
        # Stop auto-refresh timer
        self.auto_refresh_timer.stop()
        super().closeEvent(event)
