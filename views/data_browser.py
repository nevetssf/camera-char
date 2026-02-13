"""
Data browser view for displaying and filtering aggregate analysis data.
Provides table view with filter controls and search functionality.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QGroupBox, QListWidget, QAbstractItemView, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QVariant
from PyQt6.QtGui import QFont
import pandas as pd
from typing import Optional, List, Any

from models.data_model import DataModel


class PandasTableModel(QAbstractTableModel):
    """Qt table model for pandas DataFrame"""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize table model.

        Args:
            data: Pandas DataFrame
        """
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()) -> int:
        """Get number of rows"""
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Get number of columns"""
        return len(self._data.columns) + 1  # Add 1 for Archive button column

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole) -> QVariant:
        """Get data for cell"""
        if not index.isValid():
            return QVariant()

        # Last column is for Archive button (handled separately)
        if index.column() == len(self._data.columns):
            return QVariant()

        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            column_name = self._data.columns[index.column()]

            # For 'source' column, show only filename (not full path)
            if column_name == 'source':
                from pathlib import Path
                return Path(str(value)).name

            # Format floats nicely
            if isinstance(value, float):
                return f"{value:.6f}"

            return str(value)

        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation,
                  role=Qt.ItemDataRole.DisplayRole) -> QVariant:
        """Get header data"""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == len(self._data.columns):
                    return "Archive"
                return str(self._data.columns[section])
            else:
                return str(section + 1)

        return QVariant()

    def update_data(self, data: pd.DataFrame) -> None:
        """Update the model with new data"""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def get_row_data(self, row: int) -> pd.Series:
        """Get data for a specific row"""
        return self._data.iloc[row]


class DataBrowser(QWidget):
    """Data browser widget with table and filters"""

    # Signals
    row_selected = pyqtSignal(int)  # Emitted when a row is selected
    data_filtered = pyqtSignal()    # Emitted when filters are applied

    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize data browser.

        Args:
            csv_path: Path to aggregate_analysis.csv (uses config if None)
        """
        super().__init__()

        # Get CSV path from config if not provided
        if csv_path is None:
            from utils.config_manager import get_config
            config = get_config()
            csv_path = str(config.get_aggregate_csv_path())

        # Initialize data model
        self.data_model = DataModel(csv_path=csv_path)

        # Source directory for raw files - get from config
        from utils.config_manager import get_config
        config = get_config()
        source_dir = config.get_source_dir()
        if source_dir and source_dir.exists():
            self.source_directory = str(source_dir)
        else:
            self.source_directory = None

        # Create UI
        self._create_ui()
        self._load_initial_data()

    def _create_ui(self) -> None:
        """Create the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        title_label = QLabel("Data Browser")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Filter controls
        filter_group = self._create_filter_controls()
        layout.addWidget(filter_group)

        # Browse button for source files
        browse_layout = QHBoxLayout()
        browse_label = QLabel("Source:")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_source)
        browse_layout.addWidget(browse_label)
        browse_layout.addWidget(self.browse_button)
        browse_layout.addStretch()
        layout.addLayout(browse_layout)

        # Source path label
        self.source_path_label = QLabel("No source directory selected")
        self.source_path_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.source_path_label)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Table view
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.clicked.connect(self._on_row_clicked)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table_view)

        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

    def _create_filter_controls(self) -> QGroupBox:
        """Create filter control group"""
        group = QGroupBox("Filters")
        layout = QVBoxLayout()
        group.setLayout(layout)

        # Camera filter
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Cameras:")
        self.camera_list = QListWidget()
        self.camera_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.camera_list.setMaximumHeight(120)
        self.camera_list.itemSelectionChanged.connect(self._on_filter_changed)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_list)
        layout.addLayout(camera_layout)

        # ISO filter
        iso_layout = QHBoxLayout()
        iso_label = QLabel("ISOs:")
        self.iso_list = QListWidget()
        self.iso_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.iso_list.setMaximumHeight(100)
        self.iso_list.itemSelectionChanged.connect(self._on_filter_changed)
        iso_layout.addWidget(iso_label)
        iso_layout.addWidget(self.iso_list)
        layout.addLayout(iso_layout)

        # Reset button
        self.reset_button = QPushButton("Reset Filters")
        self.reset_button.clicked.connect(self._on_reset_filters)
        layout.addWidget(self.reset_button)

        return group

    def _load_initial_data(self) -> None:
        """Load initial data into table and populate filters"""
        # Populate camera list
        cameras = self.data_model.get_unique_cameras()
        self.camera_list.clear()
        for camera in cameras:
            self.camera_list.addItem(camera)

        # Populate ISO list
        isos = self.data_model.get_unique_isos()
        self.iso_list.clear()
        for iso in isos:
            self.iso_list.addItem(str(iso))

        # Update source path label if directory was set
        if self.source_directory:
            self.source_path_label.setText(f"📁 {self.source_directory}")
            self.source_path_label.setStyleSheet("color: black;")

        # Load data into table
        self._update_table()

    def _update_table(self) -> None:
        """Update table view with current filtered data"""
        data = self.data_model.get_data()

        # Create or update table model
        if self.table_view.model() is None:
            model = PandasTableModel(data)
            self.table_view.setModel(model)
        else:
            self.table_view.model().update_data(data)

        # Add Archive buttons to the last column
        num_cols = self.table_view.model().columnCount()
        archive_col = num_cols - 1

        for row in range(self.table_view.model().rowCount()):
            archive_btn = QPushButton("Archive")
            archive_btn.setMaximumWidth(80)
            archive_btn.clicked.connect(lambda checked, r=row: self._on_archive_file(r))
            self.table_view.setIndexWidget(
                self.table_view.model().index(row, archive_col),
                archive_btn
            )

        # Update status
        total = self.data_model.get_total_row_count()
        filtered = self.data_model.get_row_count()
        self.status_label.setText(f"Showing {filtered} of {total} rows")

        # Resize columns to content
        self.table_view.resizeColumnsToContents()

    def _on_filter_changed(self) -> None:
        """Handle filter selection change"""
        # Get selected cameras
        selected_cameras = [
            item.text() for item in self.camera_list.selectedItems()
        ]

        # Get selected ISOs
        selected_isos = [
            int(item.text()) for item in self.iso_list.selectedItems()
        ]

        # Apply filters
        self.data_model.filter_combined(
            cameras=selected_cameras if selected_cameras else None,
            iso_values=selected_isos if selected_isos else None
        )

        # Update table
        self._update_table()

        # Emit signal
        self.data_filtered.emit()

    def _on_search(self, text: str) -> None:
        """Handle search text change"""
        if text:
            self.data_model.search(text)
        else:
            # Reapply filters without search
            self._on_filter_changed()

        self._update_table()

    def _on_reset_filters(self) -> None:
        """Handle reset filters button"""
        # Clear selections
        self.camera_list.clearSelection()
        self.iso_list.clearSelection()
        self.search_input.clear()

        # Reset data model
        self.data_model.reset_filters()

        # Update table
        self._update_table()

        # Emit signal
        self.data_filtered.emit()

    def _on_row_clicked(self, index: QModelIndex) -> None:
        """Handle row click"""
        row = index.row()
        self.row_selected.emit(row)

    def _on_row_double_clicked(self, index: QModelIndex) -> None:
        """Handle row double-click"""
        row = index.row()
        # Could open image viewer or details dialog
        self.row_selected.emit(row)

    def _on_browse_source(self) -> None:
        """Handle browse source button click"""
        # Start in current source directory if set
        start_dir = self.source_directory if self.source_directory else ""

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Source Directory",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.source_directory = directory
            self.source_path_label.setText(f"📁 {directory}")
            self.source_path_label.setStyleSheet("color: black;")

    def _on_archive_file(self, row: int) -> None:
        """Handle archive button click for a row"""
        from pathlib import Path
        from utils.app_logger import get_logger
        import shutil

        logger = get_logger()

        try:
            # Get file path for the row
            file_path = self.get_file_path_for_row(row)

            if not file_path:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Archive Failed",
                    "Cannot archive: File not found. Please ensure the source directory is set correctly."
                )
                logger.warning(f"Archive failed for row {row}: File not found")
                return

            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Archive Failed",
                    f"Cannot archive: File does not exist:\n{file_path}"
                )
                logger.warning(f"Archive failed: File does not exist: {file_path}")
                return

            # Create .archive directory in the same directory as the file
            archive_dir = file_path_obj.parent / ".archive"
            archive_dir.mkdir(exist_ok=True)
            logger.info(f"Archive directory: {archive_dir}")

            # Move file to archive directory
            destination = archive_dir / file_path_obj.name
            logger.info(f"Moving {file_path_obj} to {destination}")

            shutil.move(str(file_path_obj), str(destination))

            # Show success message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "File Archived",
                f"File archived successfully:\n{file_path_obj.name}\n\nMoved to:\n{archive_dir}"
            )
            logger.info(f"File archived successfully: {file_path_obj.name} -> {archive_dir}")

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Archive Failed",
                f"Failed to archive file:\n{str(e)}"
            )
            logger.error(f"Archive failed for row {row}: {e}", exc_info=True)

    def get_file_path_for_row(self, row: int) -> Optional[str]:
        """
        Get full file path for a specific row.

        Args:
            row: Row index

        Returns:
            Full file path or None if not available
        """
        from pathlib import Path
        from utils.app_logger import get_logger

        logger = get_logger()
        logger.debug(f"get_file_path_for_row called for row {row}")

        row_data = self.get_row_data(row)

        # Get source filename from CSV
        if 'source' not in row_data:
            logger.warning(f"'source' column not found in row data for row {row}")
            return None

        source = row_data['source']
        logger.debug(f"Source from CSV: {source}")
        logger.debug(f"Current source_directory: {self.source_directory}")

        # If source_directory is set, construct full path
        if self.source_directory:
            # Try direct join first (for simple filenames)
            file_path = Path(self.source_directory) / source
            logger.debug(f"Checking: {file_path}")
            if file_path.exists():
                logger.info(f"File found: {file_path}")
                return str(file_path)

            # If source contains absolute path from different system, extract relative portion
            # Look for common patterns like "detector-noise/" or "noise_images/"
            for pattern in ['detector-noise/', 'noise_images/', 'noise-images/']:
                if pattern in source:
                    # Extract relative path after pattern
                    relative_part = source.split(pattern, 1)[1]
                    file_path = Path(self.source_directory) / relative_part
                    logger.debug(f"Checking with extracted relative path: {file_path}")
                    if file_path.exists():
                        logger.info(f"File found with relative extraction: {file_path}")
                        return str(file_path)

            # Try just the filename (last component)
            filename = Path(source).name
            file_path = Path(self.source_directory) / filename
            logger.debug(f"Checking with filename only: {file_path}")
            if file_path.exists():
                logger.info(f"File found with filename only: {file_path}")
                return str(file_path)

        # Try as absolute path
        logger.debug(f"Trying as absolute path: {source}")
        if Path(source).exists():
            logger.info(f"File found (absolute path): {source}")
            return source

        # Try relative to current directory
        relative_path = Path(f"./{source}")
        logger.debug(f"Trying relative path: {relative_path}")
        if relative_path.exists():
            resolved = str(relative_path.resolve())
            logger.info(f"File found (relative path): {resolved}")
            return resolved

        logger.warning(f"File not found for row {row}, source: {source}")
        return None

    def get_row_data(self, row: int) -> pd.Series:
        """
        Get data for a specific row.

        Args:
            row: Row index

        Returns:
            Row data as Series
        """
        return self.data_model.get_row(row)

    def get_selected_row(self) -> Optional[int]:
        """Get currently selected row index"""
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            return indexes[0].row()
        return None

    def get_filtered_data(self) -> pd.DataFrame:
        """Get currently filtered data"""
        return self.data_model.get_data()

    def export_data(self, file_path: str) -> None:
        """
        Export filtered data to CSV.

        Args:
            file_path: Output file path
        """
        self.data_model.export_filtered_data(file_path)

    def get_selected_cameras(self) -> List[str]:
        """Get list of selected camera models"""
        return [item.text() for item in self.camera_list.selectedItems()]

    def get_selected_isos(self) -> List[int]:
        """Get list of selected ISO values"""
        return [int(item.text()) for item in self.iso_list.selectedItems()]

    def reload_data(self, csv_path: Optional[str] = None) -> None:
        """
        Reload data from CSV.

        Args:
            csv_path: New CSV path (optional)
        """
        if csv_path:
            self.data_model = DataModel(csv_path=csv_path)

        self._load_initial_data()
