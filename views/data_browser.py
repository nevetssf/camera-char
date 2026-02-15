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

    def __init__(self):
        """Initialize data browser."""
        super().__init__()

        # Initialize data model (loads from database)
        self.data_model = DataModel()

        # Source directory for raw files - get from config
        from utils.config_manager import get_config
        config = get_config()
        source_dir = config.get_source_dir()
        if source_dir and source_dir.exists():
            self.source_directory = str(source_dir)
        else:
            self.source_directory = None

        # Track if we've connected the selection signal
        self._selection_connected = False

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

        # Source path label (clickable to open in Finder)
        source_label = QLabel("Source:")
        self.source_path_label = QLabel("No source directory selected")
        self.source_path_label.setStyleSheet(
            "color: #0066cc; font-style: italic; text-decoration: underline;"
        )
        self.source_path_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.source_path_label.setToolTip("Click to open in Finder/File Explorer")
        self.source_path_label.mousePressEvent = self._on_source_path_clicked

        source_layout = QHBoxLayout()
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_path_label)
        source_layout.addStretch()
        layout.addLayout(source_layout)

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
        """Create filter control group with 3 customizable columns"""
        group = QGroupBox("Filters")
        main_layout = QVBoxLayout()
        group.setLayout(main_layout)

        # Filter options (limited to 4 choices)
        self.filter_options = [
            ('camera', 'Camera'),
            ('iso', 'ISO'),
            ('exposure_setting', 'Exposure Setting'),
            ('exposure_time', 'Exposure Time'),
        ]

        # Column labels: Filter, Group, X-Axis
        self.column_labels = ['Filter', 'Group', 'X-Axis']

        # Create 3 filter columns
        columns_layout = QHBoxLayout()

        self.filter_columns = []
        for i in range(3):
            col_widget, col_data = self._create_filter_column(i)
            self.filter_columns.append(col_data)
            columns_layout.addWidget(col_widget)

        main_layout.addLayout(columns_layout)

        # Reset button
        self.reset_button = QPushButton("Reset Filters")
        self.reset_button.clicked.connect(self._on_reset_filters)
        main_layout.addWidget(self.reset_button)

        return group

    def _create_filter_column(self, index: int) -> tuple:
        """Create a single filter column"""
        # Default filters: camera, iso, exposure_time
        default_filters = ['camera', 'iso', 'exposure_time']
        default_filter = default_filters[index] if index < len(default_filters) else 'camera'

        col_widget = QWidget()
        col_layout = QVBoxLayout()
        col_widget.setLayout(col_layout)

        # Add column label
        label = QLabel(self.column_labels[index])
        label_font = QFont()
        label_font.setBold(True)
        label.setFont(label_font)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col_layout.addWidget(label)

        # Dropdown to select filter type
        type_combo = QComboBox()
        # Initially populate with all options (will be filtered later)
        self._populate_filter_type_combo(type_combo, index, default_filter)

        type_combo.currentIndexChanged.connect(lambda: self._on_filter_type_changed(index))

        col_layout.addWidget(type_combo)

        # List widget for filter values
        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        list_widget.setMaximumHeight(200)
        list_widget.itemSelectionChanged.connect(lambda: self._on_filter_changed(index))
        col_layout.addWidget(list_widget)

        return col_widget, {
            'type_combo': type_combo,
            'list_widget': list_widget,
            'current_type': default_filter
        }

    def _populate_filter_type_combo(self, combo: QComboBox, column_index: int, current_selection: str = None) -> None:
        """
        Populate filter type combo, excluding filters already selected in previous columns.

        Args:
            combo: The QComboBox to populate
            column_index: Index of this column (0, 1, or 2)
            current_selection: Current selection to maintain (optional)
        """
        # Get filter types already selected in previous columns
        excluded_types = set()
        for i in range(column_index):
            if i < len(self.filter_columns):
                excluded_types.add(self.filter_columns[i]['current_type'])

        # Clear and repopulate combo
        combo.blockSignals(True)  # Prevent triggering change events
        combo.clear()

        selected_idx = 0
        for idx, (key, label) in enumerate(self.filter_options):
            if key not in excluded_types:
                combo.addItem(label, key)
                if key == current_selection:
                    selected_idx = combo.count() - 1

        # Set the current selection
        if combo.count() > 0:
            combo.setCurrentIndex(selected_idx)

        combo.blockSignals(False)

    def _on_filter_type_changed(self, column_index: int) -> None:
        """Handle filter type change"""
        col_data = self.filter_columns[column_index]
        combo = col_data['type_combo']
        new_type = combo.currentData()
        col_data['current_type'] = new_type

        # Repopulate type combos in subsequent columns to exclude this selection
        for i in range(column_index + 1, len(self.filter_columns)):
            next_col_data = self.filter_columns[i]
            current_selection = next_col_data['current_type']
            self._populate_filter_type_combo(next_col_data['type_combo'], i, current_selection)
            # Update current_type in case it changed
            next_col_data['current_type'] = next_col_data['type_combo'].currentData()

        # Repopulate the list with new filter values
        self._populate_filter_column(column_index)

        # Repopulate subsequent filter value lists
        for i in range(column_index + 1, len(self.filter_columns)):
            self._populate_filter_column(i)

        # Reapply filters
        self._on_filter_changed(column_index)

    def _populate_filter_column(self, column_index: int) -> None:
        """Populate a filter column with values based on previous filters (cascading)"""
        col_data = self.filter_columns[column_index]
        filter_type = col_data['current_type']
        list_widget = col_data['list_widget']

        list_widget.clear()

        # Get data filtered by previous columns (cascading filter)
        if column_index == 0:
            # First column: use full dataset
            data_source = self.data_model.full_data
        else:
            # Subsequent columns: apply filters from previous columns only
            filters = {}
            for i in range(column_index):
                prev_col_data = self.filter_columns[i]
                prev_filter_type = prev_col_data['current_type']
                prev_list_widget = prev_col_data['list_widget']

                selected_items = prev_list_widget.selectedItems()
                if selected_items:
                    selected_values = [
                        item.data(Qt.ItemDataRole.UserRole) for item in selected_items
                    ]
                    filters[prev_filter_type] = selected_values

            # Apply previous filters to get data source
            if filters:
                data_source = self.data_model.full_data.copy()
                for field, values in filters.items():
                    data_source = data_source[data_source[field].isin(values)]
            else:
                data_source = self.data_model.full_data

        # Get unique values from the filtered data source
        if filter_type == 'camera':
            values = sorted(data_source['camera'].unique().tolist()) if 'camera' in data_source.columns else []
            items = [str(v) for v in values]
        elif filter_type == 'iso':
            values = sorted([x for x in data_source['iso'].unique().tolist() if pd.notna(x)]) if 'iso' in data_source.columns else []
            items = [str(v) for v in values]
        elif filter_type == 'exposure_time':
            values = sorted([x for x in data_source['exposure_time'].unique().tolist() if pd.notna(x)]) if 'exposure_time' in data_source.columns else []
            items = [f"{v:.6f}s" for v in values]
        elif filter_type == 'exposure_setting':
            values = sorted([int(x) for x in data_source['exposure_setting'].unique().tolist() if pd.notna(x)]) if 'exposure_setting' in data_source.columns else []
            items = [f"1/{v}" for v in values]
        elif filter_type == 'bits_per_sample':
            values = sorted([x for x in data_source['bits_per_sample'].unique().tolist() if pd.notna(x)]) if 'bits_per_sample' in data_source.columns else []
            items = [f"{v} bit" for v in values]
        elif filter_type == 'megapixels':
            values = sorted([x for x in data_source['megapixels'].unique().tolist() if pd.notna(x)]) if 'megapixels' in data_source.columns else []
            items = [f"{v:.1f} MP" for v in values]
        else:
            values = []
            items = []

        # Store actual values as item data
        for value, display in zip(values, items):
            list_widget.addItem(display)
            list_widget.item(list_widget.count() - 1).setData(Qt.ItemDataRole.UserRole, value)

    def _load_initial_data(self) -> None:
        """Load initial data into table and populate filters"""
        # Populate all filter columns
        for i in range(len(self.filter_columns)):
            self._populate_filter_column(i)

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

        # Connect selection changed signal (only once)
        if not self._selection_connected:
            selection_model = self.table_view.selectionModel()
            if selection_model:
                selection_model.selectionChanged.connect(self._on_selection_changed)
                self._selection_connected = True

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

    def _on_filter_changed(self, column_index: Optional[int] = None) -> None:
        """Handle filter selection change"""
        # Repopulate subsequent filter columns (cascading effect)
        if column_index is not None:
            for i in range(column_index + 1, len(self.filter_columns)):
                # Save current selection
                col_data = self.filter_columns[i]
                list_widget = col_data['list_widget']
                selected_values = [
                    item.data(Qt.ItemDataRole.UserRole) for item in list_widget.selectedItems()
                ]

                # Repopulate with cascaded values
                self._populate_filter_column(i)

                # Restore selection where possible
                for j in range(list_widget.count()):
                    item = list_widget.item(j)
                    if item.data(Qt.ItemDataRole.UserRole) in selected_values:
                        item.setSelected(True)

        # Collect filters from all columns
        filters = {}

        for col_data in self.filter_columns:
            filter_type = col_data['current_type']
            list_widget = col_data['list_widget']

            selected_items = list_widget.selectedItems()
            if selected_items:
                # Get actual values from item data
                selected_values = [
                    item.data(Qt.ItemDataRole.UserRole) for item in selected_items
                ]
                filters[filter_type] = selected_values

        # Apply combined filters
        self.data_model.filter_by_multiple_fields(filters)

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
        # Clear selections in all filter columns
        for col_data in self.filter_columns:
            col_data['list_widget'].clearSelection()

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

    def _on_selection_changed(self, selected, deselected) -> None:
        """Handle selection change (e.g., from arrow key navigation)"""
        # Get the currently selected row
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            self.row_selected.emit(row)

    def _on_source_path_clicked(self, event) -> None:
        """Handle source path label click - open directory in Finder/Explorer"""
        from utils.config_manager import get_config
        import subprocess
        import sys

        config = get_config()
        source_dir = config.get_source_dir()

        if source_dir and Path(source_dir).exists():
            try:
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', source_dir])
                elif sys.platform == 'win32':  # Windows
                    subprocess.run(['explorer', source_dir])
                else:  # Linux
                    subprocess.run(['xdg-open', source_dir])
            except Exception as e:
                print(f"Error opening directory: {e}")

    def _on_archive_file(self, row: int) -> None:
        """Handle archive button click for a row"""
        from pathlib import Path
        from utils.app_logger import get_logger
        from utils.db_manager import get_db_manager
        import shutil

        logger = get_logger()
        db = get_db_manager()

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

            # Get image record from database to get image_id
            image_record = db.get_image_by_path(file_path_obj)

            # Create .archive directory in the same directory as the file
            archive_dir = file_path_obj.parent / ".archive"
            archive_dir.mkdir(exist_ok=True)
            logger.info(f"Archive directory: {archive_dir}")

            # Move file to archive directory
            destination = archive_dir / file_path_obj.name
            logger.info(f"Moving {file_path_obj} to {destination}")

            shutil.move(str(file_path_obj), str(destination))

            # Mark image as archived in database if found
            if image_record:
                db.mark_archived(image_record['id'], archived=True)
                logger.info(f"Marked image ID {image_record['id']} as archived in database")

            # Reload data to update the table (removes archived images)
            self.reload_data()

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

    def get_group_parameter(self) -> str:
        """Get the parameter to group by (from column 2)"""
        if len(self.filter_columns) >= 2:
            return self.filter_columns[1]['current_type']
        return 'camera'  # Default fallback

    def get_xaxis_parameter(self) -> str:
        """Get the parameter for x-axis (from column 3)"""
        if len(self.filter_columns) >= 3:
            return self.filter_columns[2]['current_type']
        return 'iso'  # Default fallback

    def get_group_selected_values(self) -> List[Any]:
        """Get selected values from group column (column 2)"""
        if len(self.filter_columns) >= 2:
            col_data = self.filter_columns[1]
            list_widget = col_data['list_widget']
            return [item.data(Qt.ItemDataRole.UserRole) for item in list_widget.selectedItems()]
        return []

    def get_xaxis_selected_values(self) -> List[Any]:
        """Get selected values from x-axis column (column 3)"""
        if len(self.filter_columns) >= 3:
            col_data = self.filter_columns[2]
            list_widget = col_data['list_widget']
            return [item.data(Qt.ItemDataRole.UserRole) for item in list_widget.selectedItems()]
        return []

    def export_data(self, file_path: str) -> None:
        """
        Export filtered data to CSV.

        Args:
            file_path: Output file path
        """
        self.data_model.export_filtered_data(file_path)

    def get_selected_cameras(self) -> List[str]:
        """Get list of selected camera models"""
        for col_data in self.filter_columns:
            if col_data['current_type'] == 'camera':
                return [item.data(Qt.ItemDataRole.UserRole)
                       for item in col_data['list_widget'].selectedItems()]
        return []

    def get_selected_isos(self) -> List[int]:
        """Get list of selected ISO values"""
        for col_data in self.filter_columns:
            if col_data['current_type'] == 'iso':
                return [item.data(Qt.ItemDataRole.UserRole)
                       for item in col_data['list_widget'].selectedItems()]
        return []

    def reload_data(self) -> None:
        """Reload data from database."""
        # Create new data model instance (reloads from database)
        self.data_model = DataModel()
        self._load_initial_data()
