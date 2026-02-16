"""
Metadata viewer widget for displaying complete file metadata.
Shows metadata in a table format with categorization and search.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QImage
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path

from utils.image_loader import get_image_loader, normalize_for_display
from views.image_window import ImageWindow


class ImageViewer(QWidget):
    """Metadata viewer widget with popup image window"""

    image_loaded = pyqtSignal(str)  # Emitted when image is loaded

    def __init__(self):
        """Initialize metadata viewer"""
        super().__init__()

        self.image_loader = get_image_loader()
        self.current_file_path: Optional[str] = None
        self.current_camera_model: Optional[str] = None
        self.current_metadata: Optional[Dict[str, Any]] = None
        self.current_pixmap: Optional[QPixmap] = None
        self.current_display_array: Optional[np.ndarray] = None
        self.current_raw_data: Optional[np.ndarray] = None
        self.current_stats: Optional[Dict[str, Any]] = None
        self.current_file_hash: Optional[str] = None
        self.current_camera_id: Optional[int] = None

        # Persistent image window
        self.image_window: Optional[ImageWindow] = None

        self._create_ui()

    def _create_ui(self) -> None:
        """Create user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header with controls
        header_layout = QHBoxLayout()

        self.filename_label = QLabel("No file loaded")
        filename_font = QFont()
        filename_font.setPointSize(12)
        filename_font.setBold(True)
        self.filename_label.setFont(filename_font)
        header_layout.addWidget(self.filename_label)

        header_layout.addStretch()

        # Pop out image button
        self.btn_pop_out_image = QPushButton("🖼️ View Image")
        self.btn_pop_out_image.clicked.connect(self._on_pop_out_image)
        self.btn_pop_out_image.setEnabled(False)
        header_layout.addWidget(self.btn_pop_out_image)

        # Search box
        search_label = QLabel("Search:")
        header_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search metadata...")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self._filter_table)
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

        # Use appropriate font for readability
        table_font = QFont("Courier New", 15)
        self.table.setFont(table_font)

        layout.addWidget(self.table)

        # Status bar
        self.status_label = QLabel("No metadata loaded")
        layout.addWidget(self.status_label)

        # Store full metadata for filtering
        self.full_metadata = []

    def load_image(self, file_path: str, fast_preview: bool = False,
                  camera_model: Optional[str] = None) -> None:
        """
        Load and display image metadata.

        Args:
            file_path: Path to image file
            fast_preview: Use fast preview mode
            camera_model: Camera model for crop lookup
        """
        from utils.app_logger import get_logger
        import rawpy
        from PyQt6.QtGui import QPixmap, QImage
        from sensor_camera import Sensor
        logger = get_logger()

        try:
            logger.info(f"Loading image: {file_path}")
            logger.debug(f"  fast_preview: {fast_preview}, camera_model: {camera_model}")

            # Load raw data directly without color processing (greyscale)
            logger.debug("Loading raw greyscale data")
            with rawpy.imread(str(file_path)) as raw:
                # Get raw pixel data (greyscale)
                raw_data = raw.raw_image.copy()

                # Apply camera-specific crop if available
                crop = Sensor.CAMERA_CROPS.get(camera_model) if camera_model else None
                if crop is not None:
                    logger.debug(f"Applying crop for {camera_model}")
                    raw_data = raw_data[crop]

                # Calculate statistics
                mean_val = float(np.mean(raw_data))
                std_val = float(np.std(raw_data))
                ydim, xdim = raw_data.shape
                bit_depth = raw_data.dtype.itemsize * 8
                min_val = int(np.min(raw_data))
                max_val = int(np.max(raw_data))

                logger.debug(f"Image loaded, shape: {raw_data.shape}, dtype: {raw_data.dtype}, greyscale")

                # Normalize to 8-bit for display
                if raw_data.dtype == np.uint16:
                    display_array = (raw_data.astype(np.float32) / 65535.0 * 255.0).astype(np.uint8)
                elif raw_data.dtype == np.uint8:
                    display_array = raw_data
                else:
                    # For other types, normalize to full range
                    if max_val > min_val:
                        display_array = ((raw_data.astype(np.float32) - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                    else:
                        display_array = np.zeros_like(raw_data, dtype=np.uint8)

                # Convert to QImage (greyscale)
                bytes_per_line = xdim
                qimage = QImage(display_array.data, xdim, ydim, bytes_per_line, QImage.Format.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimage)
                logger.debug(f"QPixmap created, size: {pixmap.width()}x{pixmap.height()}, greyscale")

                # Prepare statistics dictionary
                stats = {
                    'bit_depth': bit_depth,
                    'width': xdim,
                    'height': ydim,
                    'mean': mean_val,
                    'std': std_val,
                    'min': min_val,
                    'max': max_val
                }

            # Calculate file hash and look up camera ID
            file_hash = None
            camera_id = None
            try:
                from utils.db_manager import get_db_manager
                db = get_db_manager()
                file_hash = db.calculate_file_hash(Path(file_path))
                camera_id = db.get_camera_id_by_file_hash(file_hash)
                logger.debug(f"Looked up camera_id={camera_id} from file hash")
            except Exception as e:
                logger.debug(f"Could not look up camera ID: {e}")

            # Store for popup window
            self.current_pixmap = pixmap
            self.current_display_array = display_array
            self.current_file_path = file_path
            self.current_camera_model = camera_model
            self.current_raw_data = raw_data
            self.current_stats = stats
            self.current_file_hash = file_hash
            self.current_camera_id = camera_id

            # Load and display metadata
            logger.debug("Loading metadata")
            self._load_metadata(file_path)

            # Enable pop out button
            self.btn_pop_out_image.setEnabled(True)

            # Update image window if it's open
            if self.image_window and self.image_window.isVisible():
                self.image_window.load_image(
                    pixmap, display_array, file_path,
                    stats=stats, raw_data=raw_data,
                    file_hash=file_hash, camera_id=camera_id
                )

            # Emit signal
            logger.info(f"Image loaded successfully: {Path(file_path).name}")
            self.image_loaded.emit(file_path)

        except Exception as e:
            logger.error(f"Failed to load image: {file_path}", exc_info=True)
            self.filename_label.setText(f"Error loading: {Path(file_path).name}")
            self.status_label.setText(f"Error: {str(e)}")
            raise

    def _numpy_to_pixmap(self, image_array: np.ndarray) -> QPixmap:
        """
        Convert numpy array to QPixmap.

        Args:
            image_array: Image as numpy array

        Returns:
            QPixmap
        """
        # Ensure array is contiguous
        if not image_array.flags['C_CONTIGUOUS']:
            image_array = np.ascontiguousarray(image_array)

        height, width = image_array.shape[:2]

        if len(image_array.shape) == 2:
            # Grayscale (2D array)
            bytes_per_line = width
            q_image = QImage(
                image_array.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_Grayscale8
            )
        elif image_array.shape[2] == 1:
            # Grayscale with single channel dimension (H, W, 1)
            # Squeeze to 2D
            image_array_2d = image_array.squeeze()
            bytes_per_line = width
            q_image = QImage(
                image_array_2d.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_Grayscale8
            )
        else:
            # RGB (H, W, 3)
            bytes_per_line = 3 * width
            q_image = QImage(
                image_array.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )

        return QPixmap.fromImage(q_image)

    def _load_metadata(self, file_path: str) -> None:
        """Load metadata from raw file"""
        from utils.app_logger import get_logger
        logger = get_logger()

        try:
            logger.debug("Loading metadata with ExifTool")
            from utils.exiftool_helper import get_exiftool_helper

            with get_exiftool_helper() as et:
                metadata_list = et.get_metadata([file_path])
                if not metadata_list:
                    self.current_metadata = {}
                    self.filename_label.setText(f"📄 {Path(file_path).name}")
                    self.status_label.setText("No metadata available")
                    return

                metadata = metadata_list[0]
                self.current_metadata = metadata
                logger.debug(f"Loaded {len(metadata)} metadata fields")

                # Update display
                self.filename_label.setText(f"📄 {Path(file_path).name}")
                self._display_metadata(file_path, metadata)

        except Exception as e:
            logger.error(f"Failed to load metadata: {e}", exc_info=True)
            self.current_metadata = {}
            self.filename_label.setText(f"📄 {Path(file_path).name}")
            self.status_label.setText(f"Error loading metadata: {str(e)}")

    def _display_metadata(self, file_path: str, metadata: Dict[str, Any]) -> None:
        """Display metadata in table"""
        # Organize metadata by category
        categorized = self._categorize_metadata(metadata)

        # Store for filtering
        self.full_metadata = categorized

        # Populate table
        self._populate_table(categorized)

        # Update status
        self.status_label.setText(f"{len(metadata)} metadata fields")

        # Re-apply search filter if there's text in the search box
        if self.search_input.text():
            self._filter_table(self.search_input.text())

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

    def _on_pop_out_image(self) -> None:
        """Pop out the image window"""
        if self.current_pixmap is None or self.current_display_array is None or not self.current_file_path:
            return

        # Create window if it doesn't exist
        if self.image_window is None:
            self.image_window = ImageWindow(self)

        # Load image with all data for greyscale display and analysis
        self.image_window.load_image(
            self.current_pixmap,
            self.current_display_array,
            self.current_file_path,
            stats=self.current_stats,
            raw_data=self.current_raw_data,
            file_hash=self.current_file_hash,
            camera_id=self.current_camera_id
        )

        # Show the window
        self.image_window.show()
        self.image_window.raise_()
        self.image_window.activateWindow()

    def clear_cache(self) -> None:
        """Clear image cache"""
        self.image_loader.clear_cache()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return self.image_loader.get_cache_stats()
