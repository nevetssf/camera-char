"""
Metadata window for displaying complete file metadata.
Persists across image loads and updates dynamically.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Dict, Any, Optional


class MetadataWindow(QDialog):
    """Window for displaying complete file metadata in table format"""

    def __init__(self, parent=None):
        """
        Initialize metadata window.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("File Metadata")
        self.resize(900, 700)

        # Don't close on escape or clicking outside
        self.setModal(False)

        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header with filename
        header_layout = QHBoxLayout()
        self.filename_label = QLabel("No file loaded")
        filename_font = QFont()
        filename_font.setPointSize(12)
        filename_font.setBold(True)
        self.filename_label.setFont(filename_font)
        header_layout.addWidget(self.filename_label)
        header_layout.addStretch()

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search metadata...")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self._filter_table)
        header_layout.addWidget(QLabel("Search:"))
        header_layout.addWidget(self.search_input)

        layout.addLayout(header_layout)

        # Metadata table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Category", "Key", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)

        # Use monospace font for values
        table_font = QFont("Courier New", 10)
        self.table.setFont(table_font)

        layout.addWidget(self.table)

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("No metadata loaded")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.hide)
        status_layout.addWidget(self.close_button)

        layout.addLayout(status_layout)

        # Store full metadata for filtering
        self.full_metadata = []

    def update_metadata(self, file_path: str, metadata: Dict[str, Any]) -> None:
        """
        Update the metadata display with new data.

        Args:
            file_path: Path to the file
            metadata: Dictionary of metadata key-value pairs
        """
        # Update filename
        self.filename_label.setText(f"📄 {Path(file_path).name}")

        # Organize metadata by category
        categorized = self._categorize_metadata(metadata)

        # Store for filtering
        self.full_metadata = categorized

        # Populate table
        self._populate_table(categorized)

        # Update status
        self.status_label.setText(f"{len(metadata)} metadata fields")

        # Clear search
        self.search_input.clear()

    def _categorize_metadata(self, metadata: Dict[str, Any]) -> list:
        """
        Organize metadata into categories.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            List of tuples (category, key, value)
        """
        # Define category mappings
        category_map = {
            "File": ["File:"],
            "Camera": ["EXIF:Make", "EXIF:Model", "EXIF:SerialNumber", "EXIF:InternalSerialNumber",
                      "EXIF:LensMake", "EXIF:LensModel", "EXIF:LensSerialNumber"],
            "Exposure": ["EXIF:ISO", "EXIF:ExposureTime", "EXIF:ShutterSpeed", "EXIF:FNumber",
                        "EXIF:Aperture", "EXIF:ExposureProgram", "EXIF:ExposureMode",
                        "EXIF:MeteringMode", "EXIF:ExposureCompensation", "EXIF:Flash",
                        "EXIF:FocalLength", "EXIF:FocalLengthIn35mmFormat"],
            "Image": ["EXIF:ImageWidth", "EXIF:ImageHeight", "EXIF:Orientation", "EXIF:BitsPerSample",
                     "EXIF:SamplesPerPixel", "EXIF:PhotometricInterpretation", "EXIF:Compression",
                     "File:ImageWidth", "File:ImageHeight", "Composite:ImageSize", "Composite:Megapixels"],
            "Color": ["EXIF:ColorSpace", "EXIF:WhiteBalance", "EXIF:ColorTemperature",
                     "EXIF:ColorMatrix1", "EXIF:ColorMatrix2", "EXIF:CalibrationIlluminant1",
                     "EXIF:CalibrationIlluminant2", "EXIF:AsShotNeutral", "EXIF:BaselineExposure"],
            "Date/Time": ["EXIF:DateTimeOriginal", "EXIF:CreateDate", "EXIF:ModifyDate",
                         "EXIF:OffsetTime", "EXIF:OffsetTimeOriginal", "EXIF:SubSecTime",
                         "File:FileModifyDate", "File:FileAccessDate"],
            "GPS": ["GPS:"],
            "DNG": ["EXIF:DNGVersion", "EXIF:DNGBackwardVersion", "EXIF:UniqueCameraModel",
                   "EXIF:BlackLevel", "EXIF:WhiteLevel", "EXIF:DefaultCropOrigin", "EXIF:DefaultCropSize",
                   "EXIF:ActiveArea", "EXIF:AnalogBalance"],
            "MakerNotes": ["MakerNotes:", "Leica:"],
            "Composite": ["Composite:"]
        }

        result = []
        assigned_keys = set()

        # First pass: assign to specific categories
        for category, patterns in category_map.items():
            for key, value in sorted(metadata.items()):
                if key.startswith("SourceFile"):
                    continue

                # Check if key matches category pattern
                matched = False
                for pattern in patterns:
                    if pattern in category_map["Camera"] or pattern in category_map["Exposure"] or \
                       pattern in category_map["Image"] or pattern in category_map["Color"] or \
                       pattern in category_map["Date/Time"] or pattern in category_map["DNG"]:
                        # Exact match for specific keys
                        if key == pattern:
                            matched = True
                            break
                    else:
                        # Prefix match for namespace categories
                        if key.startswith(pattern):
                            matched = True
                            break

                if matched:
                    display_key = key.split(':')[-1] if ':' in key else key
                    display_value = self._format_value(value)
                    result.append((category, display_key, display_value))
                    assigned_keys.add(key)

        # Second pass: remaining items go to "Other"
        for key, value in sorted(metadata.items()):
            if key not in assigned_keys and not key.startswith("SourceFile"):
                display_key = key.split(':')[-1] if ':' in key else key
                display_value = self._format_value(value)
                result.append(("Other", display_key, display_value))

        return result

    def _format_value(self, value: Any) -> str:
        """Format metadata value for display"""
        if isinstance(value, (list, tuple)):
            # For arrays, show first few elements if long
            if len(value) > 20:
                preview = ', '.join(str(v) for v in value[:20])
                return f"[{preview}... ({len(value)} items)]"
            return f"[{', '.join(str(v) for v in value)}]"
        elif isinstance(value, float):
            # Format floats nicely
            if abs(value) < 0.0001 or abs(value) > 1000000:
                return f"{value:.6e}"
            return f"{value:.6f}".rstrip('0').rstrip('.')
        elif isinstance(value, int) and abs(value) > 1000000:
            # Format large numbers with commas
            return f"{value:,}"
        else:
            return str(value)

    def _populate_table(self, categorized: list) -> None:
        """Populate the table with categorized metadata"""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(categorized))

        for row, (category, key, value) in enumerate(categorized):
            # Category column
            cat_item = QTableWidgetItem(category)
            cat_item.setForeground(Qt.GlobalColor.blue)
            self.table.setItem(row, 0, cat_item)

            # Key column
            key_item = QTableWidgetItem(key)
            key_font = QFont()
            key_font.setBold(True)
            key_item.setFont(key_font)
            self.table.setItem(row, 1, key_item)

            # Value column
            value_item = QTableWidgetItem(value)
            self.table.setItem(row, 2, value_item)

        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def _filter_table(self, search_text: str) -> None:
        """Filter table rows based on search text"""
        search_text = search_text.lower()

        for row in range(self.table.rowCount()):
            # Check if search text matches category, key, or value
            matches = False
            for col in range(3):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    matches = True
                    break

            self.table.setRowHidden(row, not matches)

    def clear(self) -> None:
        """Clear all metadata"""
        self.filename_label.setText("No file loaded")
        self.table.setRowCount(0)
        self.status_label.setText("No metadata loaded")
        self.search_input.clear()
