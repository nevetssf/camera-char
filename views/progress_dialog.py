"""
Custom progress dialog for long-running operations.
Shows progress, cancel button, and status message.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ProgressDialog(QDialog):
    """Custom progress dialog with progress text, cancel button, and status"""

    cancel_requested = pyqtSignal()

    def __init__(self, title: str, parent=None):
        """
        Initialize progress dialog.

        Args:
            title: Window title
            parent: Parent widget
        """
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(500, 200)

        # Create UI
        self._create_ui()

    def _create_ui(self):
        """Create user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Progress label (large text at top)
        self.progress_label = QLabel("Preparing...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.progress_label.setFont(font)
        self.progress_label.setMinimumHeight(40)
        layout.addWidget(self.progress_label)

        # Cancel button (centered)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addStretch()

        # Status label (small text at bottom)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        self.status_label.setMinimumHeight(30)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

    def set_progress(self, text: str):
        """
        Set progress text.

        Args:
            text: Progress text to display
        """
        self.progress_label.setText(text)

    def set_status(self, text: str):
        """
        Set status text at bottom.

        Args:
            text: Status text to display
        """
        self.status_label.setText(text)

    def _on_cancel(self):
        """Handle cancel button click"""
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.cancel_requested.emit()

    def was_cancelled(self) -> bool:
        """
        Check if cancel was requested.

        Returns:
            True if cancel button was clicked
        """
        return not self.cancel_button.isEnabled()
