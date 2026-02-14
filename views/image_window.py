"""
Image viewer window - popup window for viewing images with zoom controls.
Persists across image loads and updates dynamically.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QLabel, QPushButton, QFileDialog,
    QCheckBox, QSpinBox, QTextEdit, QGroupBox, QScrollArea, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent, QFont
import numpy as np
from pathlib import Path
from typing import Optional, Callable


class ZoomableGraphicsView(QGraphicsView):
    """Graphics view with zoom and pan capabilities"""

    def __init__(self):
        """Initialize zoomable graphics view"""
        super().__init__()

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.zoom_factor = 1.15
        self.current_zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 20.0

        self.setMouseTracking(True)
        self.current_image = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming"""
        if event.angleDelta().y() > 0:
            # Zoom in
            if self.current_zoom * self.zoom_factor <= self.max_zoom:
                self.scale(self.zoom_factor, self.zoom_factor)
                self.current_zoom *= self.zoom_factor
        else:
            # Zoom out
            if self.current_zoom / self.zoom_factor >= self.min_zoom:
                self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)
                self.current_zoom /= self.zoom_factor

    def fit_to_window(self) -> None:
        """Fit image to window"""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        transform = self.transform()
        self.current_zoom = transform.m11()

    def zoom_to_actual_size(self) -> None:
        """Reset zoom to 100%"""
        self.resetTransform()
        self.current_zoom = 1.0

    def zoom_in(self) -> None:
        """Zoom in"""
        if self.current_zoom * self.zoom_factor <= self.max_zoom:
            self.scale(self.zoom_factor, self.zoom_factor)
            self.current_zoom *= self.zoom_factor

    def zoom_out(self) -> None:
        """Zoom out"""
        if self.current_zoom / self.zoom_factor >= self.min_zoom:
            self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)
            self.current_zoom /= self.zoom_factor

    def set_image(self, image: np.ndarray) -> None:
        """Set image to display"""
        self.current_image = image


class PixelCropWindow(QDialog):
    """Window for displaying a 32x32 crop around a selected pixel"""

    def __init__(self, parent=None):
        """Initialize pixel crop window"""
        super().__init__(parent)
        self.setWindowTitle("Pixel Detail")
        self.resize(400, 450)
        self.setModal(False)

        # Store current pixel info for refresh
        self.current_raw_data = None
        self.current_y = None
        self.current_x = None
        self.current_value = None

        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Info label
        self.info_label = QLabel("Click on a bad pixel to view details")
        self.info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.info_label)

        # Graphics view
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)
        layout.addWidget(self.graphics_view, stretch=1)

        # Statistics label
        self.stats_label = QLabel("")
        stats_font = QFont("Monospace", 10)
        self.stats_label.setFont(stats_font)
        self.stats_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        layout.addWidget(self.stats_label)

    def update_crop(self, raw_data: np.ndarray, center_y: int, center_x: int,
                    pixel_value: int, auto_scale: bool, log_view: bool):
        """
        Update the window with a 32x32 crop around the specified pixel.

        Args:
            raw_data: Full raw image data
            center_y: Y coordinate of center pixel
            center_x: X coordinate of center pixel
            pixel_value: Value of the center pixel
            auto_scale: Apply auto-scaling
            log_view: Apply log view
        """
        # Store current state for refresh
        self.current_raw_data = raw_data
        self.current_y = center_y
        self.current_x = center_x
        self.current_value = pixel_value

        # Extract 32x32 region
        crop_size = 32
        half_size = crop_size // 2

        # Calculate crop bounds
        y_start = max(0, center_y - half_size)
        y_end = min(raw_data.shape[0], center_y + half_size)
        x_start = max(0, center_x - half_size)
        x_end = min(raw_data.shape[1], center_x + half_size)

        crop = raw_data[y_start:y_end, x_start:x_end].copy()

        # Apply scaling
        working_data = crop.astype(np.float32)

        if log_view:
            working_data = np.log10(working_data + 1.0)

        if auto_scale:
            min_val = np.min(working_data)
            max_val = np.max(working_data)
            if max_val > min_val:
                display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
            else:
                display_array = np.zeros_like(crop, dtype=np.uint8)
        else:
            if log_view:
                max_log = np.log10(65536.0)
                display_array = np.clip(working_data / max_log * 255.0, 0, 255).astype(np.uint8)
            else:
                display_array = (working_data / 65535.0 * 255.0).astype(np.uint8)

        # Convert to QImage
        ydim, xdim = display_array.shape
        bytes_per_line = xdim
        qimage = QImage(display_array.data, xdim, ydim, bytes_per_line, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)

        # Scale up for better visibility
        pixmap = pixmap.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio)

        # Display
        self.pixmap_item.setPixmap(pixmap)
        self.graphics_scene.setSceneRect(QRectF(pixmap.rect()))
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        # Update labels
        self.info_label.setText(f"Pixel at Row={center_y}, Col={center_x}, Value={pixel_value}")

        # Calculate statistics for the crop
        crop_mean = float(np.mean(crop))
        crop_std = float(np.std(crop))
        crop_min = int(np.min(crop))
        crop_max = int(np.max(crop))

        stats_text = (
            f"32×32 Region: Mean={crop_mean:.2f}, Std={crop_std:.2f}, "
            f"Min={crop_min}, Max={crop_max}"
        )
        self.stats_label.setText(stats_text)


class ImageWindow(QDialog):
    """Window for displaying images with zoom controls"""

    def __init__(self, parent=None, standalone: bool = False,
                 image_loader_callback: Optional[Callable] = None,
                 default_dir: Optional[str] = None):
        """
        Initialize image window.

        Args:
            parent: Parent widget
            standalone: If True, show Open button for file selection
            image_loader_callback: Callback function to load images (file_path, camera_model) -> (pixmap, display_array, stats)
            default_dir: Default directory for file dialog
        """
        super().__init__(parent)
        self.setWindowTitle("Raw Image Viewer")
        self.resize(1200, 800)

        # Don't close on escape
        self.setModal(False)

        self.standalone = standalone
        self.image_loader_callback = image_loader_callback
        self.default_dir = default_dir or str(Path.home())

        # Store current image data for re-rendering with auto-scale
        self.current_raw_data = None
        self.current_raw_data_original = None  # Original data before bad pixel removal
        self.current_file_path = None
        self.current_stats = None
        self.current_file_hash = None
        self.current_camera_id = None
        self.current_bad_pixels = None  # List of (y, x) coordinates of bad pixels

        # Projection window (created on demand)
        self.projection_window = None

        # Pixel crop window (created on demand)
        self.pixel_crop_window = None

        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Header with filename (clickable to open in Finder)
        header_layout = QHBoxLayout()
        self.filename_label = QLabel("No image loaded")
        filename_font = QFont()
        filename_font.setPointSize(11)
        filename_font.setBold(False)
        self.filename_label.setFont(filename_font)
        self.filename_label.setStyleSheet(
            "color: #0066cc; text-decoration: underline; padding: 5px;"
        )
        self.filename_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filename_label.setToolTip("Click to show in Finder")
        self.filename_label.mousePressEvent = self._on_path_clicked
        self.filename_label.setWordWrap(False)
        header_layout.addWidget(self.filename_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Top controls row
        controls_layout = QHBoxLayout()

        # Open button (only in standalone mode)
        if self.standalone:
            self.btn_open = QPushButton("Open...")
            self.btn_open.clicked.connect(self._on_open_file)
            controls_layout.addWidget(self.btn_open)
            controls_layout.addSpacing(20)

        # Auto Scale checkbox
        self.auto_scale_checkbox = QCheckBox("Auto Scale")
        self.auto_scale_checkbox.setChecked(True)  # Checked by default
        self.auto_scale_checkbox.setToolTip("Scale display so min=black, max=white")
        self.auto_scale_checkbox.stateChanged.connect(self._on_scaling_changed)
        controls_layout.addWidget(self.auto_scale_checkbox)

        # Log View checkbox
        self.log_view_checkbox = QCheckBox("Log View")
        self.log_view_checkbox.setChecked(True)  # Checked by default
        self.log_view_checkbox.setToolTip("Apply logarithmic scaling for high dynamic range data")
        self.log_view_checkbox.stateChanged.connect(self._on_scaling_changed)
        controls_layout.addWidget(self.log_view_checkbox)

        # Remove Bad Pixels checkbox
        self.remove_bad_pixels_checkbox = QCheckBox("Remove Bad Pixels")
        self.remove_bad_pixels_checkbox.setChecked(True)  # Checked by default
        self.remove_bad_pixels_checkbox.setToolTip("Replace bad pixels with mean of neighbors")
        self.remove_bad_pixels_checkbox.stateChanged.connect(self._on_scaling_changed)
        controls_layout.addWidget(self.remove_bad_pixels_checkbox)

        controls_layout.addStretch()

        # Projection button
        self.btn_projection = QPushButton("Projection")
        self.btn_projection.clicked.connect(self._on_show_projection)
        controls_layout.addWidget(self.btn_projection)

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.hide if not self.standalone else self.close)
        controls_layout.addWidget(self.close_button)

        main_layout.addLayout(controls_layout)

        # Main content area: image on left, bad pixels panel on right
        content_layout = QHBoxLayout()

        # Left side: image and zoom controls
        left_layout = QVBoxLayout()

        # Graphics view
        self.graphics_view = ZoomableGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)
        left_layout.addWidget(self.graphics_view, stretch=1)

        # Zoom controls below image
        zoom_layout = QHBoxLayout()
        self.fit_to_window_checkbox = QCheckBox("Fit to Window")
        self.fit_to_window_checkbox.setChecked(True)  # Checked by default
        self.fit_to_window_checkbox.setToolTip("Automatically fit image to window on resize")
        self.fit_to_window_checkbox.stateChanged.connect(self._on_fit_to_window_changed)
        zoom_layout.addWidget(self.fit_to_window_checkbox)

        self.btn_actual_size = QPushButton("100%")
        self.btn_actual_size.clicked.connect(self._on_actual_size)
        zoom_layout.addWidget(self.btn_actual_size)

        self.btn_zoom_in = QPushButton("Zoom In")
        self.btn_zoom_in.clicked.connect(self._on_zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("Zoom Out")
        self.btn_zoom_out.clicked.connect(self._on_zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)

        # Disable zoom buttons initially since Fit to Window is checked by default
        self.btn_actual_size.setEnabled(False)
        self.btn_zoom_in.setEnabled(False)
        self.btn_zoom_out.setEnabled(False)

        self.zoom_label = QLabel("Zoom: 100%")
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addStretch()

        left_layout.addLayout(zoom_layout)

        content_layout.addLayout(left_layout, stretch=3)

        # Right side: Bad Pixels panel
        bad_pixels_group = QGroupBox("Bad Pixels")
        bad_pixels_layout = QVBoxLayout()

        # Sigma input
        sigma_layout = QHBoxLayout()
        sigma_layout.addWidget(QLabel("Sigma (N):"))
        self.sigma_spinbox = QSpinBox()
        self.sigma_spinbox.setMinimum(1)
        self.sigma_spinbox.setMaximum(20)
        self.sigma_spinbox.setValue(6)
        self.sigma_spinbox.setToolTip("Find pixels > mean + N × std_dev")
        self.sigma_spinbox.valueChanged.connect(self._on_find_bad_pixels)
        sigma_layout.addWidget(self.sigma_spinbox)
        sigma_layout.addStretch()
        bad_pixels_layout.addLayout(sigma_layout)

        # Threshold display
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Threshold:"))
        self.threshold_field = QLineEdit()
        self.threshold_field.setReadOnly(True)
        self.threshold_field.setPlaceholderText("N/A")
        threshold_layout.addWidget(self.threshold_field)
        bad_pixels_layout.addLayout(threshold_layout)

        # Count display
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("# Bad Pixels:"))
        self.bad_pixel_count_field = QLineEdit()
        self.bad_pixel_count_field.setReadOnly(True)
        self.bad_pixel_count_field.setPlaceholderText("0")
        count_layout.addWidget(self.bad_pixel_count_field)
        bad_pixels_layout.addLayout(count_layout)

        # Expected (Normal Distribution) display
        expected_layout = QHBoxLayout()
        expected_layout.addWidget(QLabel("Expected (Normal):"))
        self.expected_count_field = QLineEdit()
        self.expected_count_field.setReadOnly(True)
        self.expected_count_field.setPlaceholderText("N/A")
        self.expected_count_field.setToolTip("Expected bad pixels for a normal distribution")
        expected_layout.addWidget(self.expected_count_field)
        bad_pixels_layout.addLayout(expected_layout)

        # Results table
        self.bad_pixels_table = QTableWidget()
        self.bad_pixels_table.setColumnCount(3)
        self.bad_pixels_table.setHorizontalHeaderLabels(["Row", "Col", "Value"])
        self.bad_pixels_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bad_pixels_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.bad_pixels_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bad_pixels_table.cellClicked.connect(self._on_bad_pixel_clicked)
        bad_pixels_layout.addWidget(self.bad_pixels_table, stretch=1)

        bad_pixels_group.setLayout(bad_pixels_layout)
        content_layout.addWidget(bad_pixels_group, stretch=1)

        main_layout.addLayout(content_layout, stretch=1)

        # Statistics panel
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("No image statistics")
        stats_font = QFont("Monospace", 11)
        self.stats_label.setFont(stats_font)
        self.stats_label.setStyleSheet("background-color: #f0f0f0; padding: 8px; border: 1px solid #ccc;")
        stats_layout.addWidget(self.stats_label)
        main_layout.addLayout(stats_layout)

        # Status bar
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

    def load_image(self, pixmap: QPixmap, display_array: np.ndarray, file_path: str,
                   stats: dict = None, raw_data: np.ndarray = None,
                   file_hash: str = None, camera_id: int = None) -> None:
        """
        Load and display an image.

        Args:
            pixmap: QPixmap to display
            display_array: Numpy array for pixel inspection
            file_path: Path to the file
            stats: Optional dictionary with image statistics
            raw_data: Optional raw image data (for auto-scale re-rendering)
            file_hash: Optional file hash for database lookup
            camera_id: Optional camera ID for loading/saving attributes
        """
        # Store current file path
        self.current_file_path = file_path

        # Calculate file hash and look up camera if not provided
        if file_hash is None and Path(file_path).exists():
            try:
                from utils.db_manager import get_db_manager
                db = get_db_manager()
                file_hash = db.calculate_file_hash(Path(file_path))
                self.current_file_hash = file_hash

                # Look up camera ID from hash
                if camera_id is None:
                    camera_id = db.get_camera_id_by_file_hash(file_hash)
                    self.current_camera_id = camera_id
                    print(f"Looked up camera_id={camera_id} from file hash")
            except Exception as e:
                print(f"Could not calculate file hash or look up camera: {e}")
        else:
            self.current_file_hash = file_hash
            self.current_camera_id = camera_id

        # Check for camera-specific crop settings
        # IMPORTANT: Crop is applied FIRST, before any other processing
        crop_applied = False
        if camera_id is not None and raw_data is not None:
            try:
                from utils.db_manager import get_db_manager
                db = get_db_manager()
                camera_attrs = db.get_camera_attributes(camera_id)

                if camera_attrs:
                    x_min = camera_attrs.get('x_min')
                    x_max = camera_attrs.get('x_max')
                    y_min = camera_attrs.get('y_min')
                    y_max = camera_attrs.get('y_max')

                    # Apply crop if all values are set
                    if all(v is not None for v in [x_min, x_max, y_min, y_max]):
                        print(f"Applying camera crop: x[{x_min}:{x_max+1}], y[{y_min}:{y_max+1}]")
                        raw_data = raw_data[y_min:y_max+1, x_min:x_max+1]
                        crop_applied = True

                        # Recalculate statistics on cropped data
                        if stats:
                            ydim, xdim = raw_data.shape
                            mean_val = float(np.mean(raw_data))
                            std_val = float(np.std(raw_data))
                            min_val = int(np.min(raw_data))
                            max_val = int(np.max(raw_data))

                            stats = {
                                'bit_depth': stats.get('bit_depth', 16),
                                'width': xdim,
                                'height': ydim,
                                'mean': mean_val,
                                'std': std_val,
                                'min': min_val,
                                'max': max_val,
                                'crop_applied': True,
                                'crop_bounds': f"x[{x_min}:{x_max}], y[{y_min}:{y_max}]"
                            }
            except Exception as e:
                print(f"Could not apply camera crop: {e}")

        # Store the cropped data as both current and original
        # Original is the base data after crop but before bad pixel removal
        self.current_raw_data = raw_data
        self.current_raw_data_original = raw_data.copy() if raw_data is not None else None

        # Update filename with full path
        self.filename_label.setText(file_path)

        # Update statistics panel if stats provided
        if stats:
            self.set_statistics(stats)

        # If Auto Scale or Log View is checked and we have raw data, apply scaling
        if (self.auto_scale_checkbox.isChecked() or self.log_view_checkbox.isChecked()) and raw_data is not None and stats is not None:
            auto_scale = self.auto_scale_checkbox.isChecked()
            log_view = self.log_view_checkbox.isChecked()
            print(f"Applying scaling on load: Auto Scale={auto_scale}, Log View={log_view}")

            # Start with raw data
            working_data = raw_data.astype(np.float32)

            # Apply log scaling first if enabled
            if log_view:
                working_data = np.log10(working_data + 1.0)

            # Then apply auto-scale or normal scaling
            if auto_scale:
                min_val = np.min(working_data)
                max_val = np.max(working_data)
                if max_val > min_val:
                    display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    display_array = np.zeros_like(raw_data, dtype=np.uint8)
            else:
                if log_view:
                    max_log = np.log10(65536.0)
                    display_array = np.clip(working_data / max_log * 255.0, 0, 255).astype(np.uint8)
                else:
                    min_val = stats.get('min', 0)
                    max_val = stats.get('max', 65535)
                    if max_val > min_val:
                        display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                    else:
                        display_array = np.zeros_like(raw_data, dtype=np.uint8)

            # Store for QImage
            self._temp_display_array = display_array

            # Create new pixmap with scaled data
            ydim, xdim = raw_data.shape
            bytes_per_line = xdim
            qimage = QImage(display_array.data, xdim, ydim, bytes_per_line, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimage)

        # Display in graphics view
        self.pixmap_item.setPixmap(pixmap)
        self.graphics_scene.setSceneRect(QRectF(pixmap.rect()))
        self.graphics_view.set_image(display_array)

        # Auto-update projection if window is open
        if self.projection_window is not None and self.projection_window.isVisible():
            filename = Path(file_path).name
            self.projection_window.update_histograms(
                self.current_raw_data, filename,
                file_hash=self.current_file_hash,
                camera_id=self.current_camera_id
            )

        # Fit to window if checkbox is checked
        # Use QTimer to ensure window is fully sized before fitting
        if self.fit_to_window_checkbox.isChecked():
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._delayed_fit_to_window)

        # Update zoom label
        self._update_zoom_label()

        # Automatically find bad pixels
        self._on_find_bad_pixels()

    def _delayed_fit_to_window(self):
        """Delayed fit to window - ensures window is sized first"""
        self.graphics_view.fit_to_window()
        self._update_zoom_label()

    def set_statistics(self, stats: dict) -> None:
        """
        Set image statistics display.

        Args:
            stats: Dictionary with keys: bit_depth, width, height, mean, std, min, max, crop_applied, crop_bounds
        """
        stats_text = (
            f"Bit Depth: {stats.get('bit_depth', 'N/A')}-bit  |  "
            f"Dimensions: {stats.get('width', 0)} × {stats.get('height', 0)}  |  "
            f"Mean: {stats.get('mean', 0):.2f}  |  "
            f"Std Dev: {stats.get('std', 0):.2f}  |  "
            f"Min: {stats.get('min', 0)}  |  "
            f"Max: {stats.get('max', 0)}"
        )

        # Add crop indicator if crop was applied
        if stats.get('crop_applied'):
            stats_text += f"  |  ⚠️ CROP ACTIVE: {stats.get('crop_bounds', '')}"

        self.stats_label.setText(stats_text)
        self.current_stats = stats

    def _on_fit_to_window_changed(self, state: int) -> None:
        """Handle fit to window checkbox change"""
        if self.fit_to_window_checkbox.isChecked():
            # Immediately fit when checked
            self.graphics_view.fit_to_window()
            self._update_zoom_label()
            # Disable manual zoom controls
            self.btn_actual_size.setEnabled(False)
            self.btn_zoom_in.setEnabled(False)
            self.btn_zoom_out.setEnabled(False)
        else:
            # Enable manual zoom controls
            self.btn_actual_size.setEnabled(True)
            self.btn_zoom_in.setEnabled(True)
            self.btn_zoom_out.setEnabled(True)

    def _on_actual_size(self) -> None:
        """Handle actual size button"""
        self.graphics_view.zoom_to_actual_size()
        self._update_zoom_label()

    def _on_zoom_in(self) -> None:
        """Handle zoom in button"""
        self.graphics_view.zoom_in()
        self._update_zoom_label()

    def _on_zoom_out(self) -> None:
        """Handle zoom out button"""
        self.graphics_view.zoom_out()
        self._update_zoom_label()

    def _on_open_file(self) -> None:
        """Handle Open button - show file dialog and load selected image"""
        # Determine starting location for file dialog
        if self.current_file_path and Path(self.current_file_path).exists():
            # Start in the directory of the currently open file and highlight it
            start_path = self.current_file_path
        else:
            # Start in the default images directory
            start_path = str(self.default_dir)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Raw Image File",
            start_path,
            "Raw Images (*.DNG *.dng *.ERF *.erf *.RAF *.raf);;All Files (*.*)"
        )

        if file_path and self.image_loader_callback:
            try:
                # Update default directory for next time
                self.default_dir = str(Path(file_path).parent)

                # Use callback to load image
                result = self.image_loader_callback(file_path)

                # Handle different return tuple sizes for backward compatibility
                if len(result) == 6:
                    pixmap, display_array, stats, raw_data, file_hash, camera_id = result
                elif len(result) == 4:
                    pixmap, display_array, stats, raw_data = result
                    file_hash = None
                    camera_id = None
                else:
                    pixmap, display_array, stats = result
                    raw_data = None
                    file_hash = None
                    camera_id = None

                # Display the image
                self.load_image(
                    pixmap, display_array, file_path,
                    stats=stats, raw_data=raw_data,
                    file_hash=file_hash, camera_id=camera_id
                )

            except Exception as e:
                # Show error in status
                self.status_label.setText(f"Error loading image: {str(e)}")
                print(f"Error loading {file_path}: {e}")
                import traceback
                traceback.print_exc()

    def _update_zoom_label(self) -> None:
        """Update zoom percentage label"""
        zoom_percent = self.graphics_view.current_zoom * 100
        self.zoom_label.setText(f"Zoom: {zoom_percent:.0f}%")

    def _on_scaling_changed(self, state: int) -> None:
        """Handle scaling checkbox changes - re-render image with new scaling"""
        if self.current_raw_data is not None and self.current_stats is not None:
            auto_scale = self.auto_scale_checkbox.isChecked()
            log_view = self.log_view_checkbox.isChecked()
            remove_bad_pixels = self.remove_bad_pixels_checkbox.isChecked()
            print(f"Scaling changed: Auto Scale={auto_scale}, Log View={log_view}, Remove Bad Pixels={remove_bad_pixels}")

            # Use cleaned data if remove bad pixels is checked and bad pixels have been found
            if remove_bad_pixels and self.current_bad_pixels is not None and len(self.current_bad_pixels) > 0:
                source_data = self.current_raw_data_original if self.current_raw_data_original is not None else self.current_raw_data
                raw_data = self._remove_bad_pixels(source_data, self.current_bad_pixels)
                print(f"  Removed {len(self.current_bad_pixels)} bad pixels")
            else:
                raw_data = self.current_raw_data_original if self.current_raw_data_original is not None else self.current_raw_data

            ydim, xdim = raw_data.shape

            # Start with raw data
            working_data = raw_data.astype(np.float32)

            # Apply log scaling first if enabled
            if log_view:
                print(f"  Applying log scaling")
                # Add 1 to avoid log(0), then apply log
                working_data = np.log10(working_data + 1.0)

            # Then apply auto-scale or normal scaling
            if auto_scale:
                # Auto-scale: scale data range to 0-255
                min_val = np.min(working_data)
                max_val = np.max(working_data)
                print(f"  Auto-scaling from {min_val:.2f} to {max_val:.2f}")
                if max_val > min_val:
                    display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    display_array = np.zeros_like(raw_data, dtype=np.uint8)
            else:
                # Normal scaling: map to full 16-bit range
                print(f"  Normal scaling")
                if log_view:
                    # For log view without auto-scale, normalize to typical log range
                    max_log = np.log10(65536.0)  # log10 of max 16-bit value
                    display_array = np.clip(working_data / max_log * 255.0, 0, 255).astype(np.uint8)
                else:
                    # Standard 16-bit to 8-bit conversion
                    if raw_data.dtype == np.uint16:
                        display_array = (working_data / 65535.0 * 255.0).astype(np.uint8)
                    elif raw_data.dtype == np.uint8:
                        display_array = raw_data.copy()
                    else:
                        min_val = np.min(working_data)
                        max_val = np.max(working_data)
                        if max_val > min_val:
                            display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                        else:
                            display_array = np.zeros_like(raw_data, dtype=np.uint8)

            # Store the display array to keep it alive for QImage
            self._temp_display_array = display_array

            # Convert to QImage and update display
            bytes_per_line = xdim
            qimage = QImage(display_array.data, xdim, ydim, bytes_per_line, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimage)

            print(f"  Updating display with new pixmap ({pixmap.width()}x{pixmap.height()})")
            self.pixmap_item.setPixmap(pixmap)
            self.graphics_scene.setSceneRect(QRectF(pixmap.rect()))
            self.graphics_view.set_image(display_array)

            # Update status
            status_parts = []
            if auto_scale:
                status_parts.append("Auto Scale: ON")
            if log_view:
                status_parts.append("Log View: ON")
            status_text = f"Image: {xdim}x{ydim} pixels"
            if status_parts:
                status_text += " | " + " | ".join(status_parts)
            self.status_label.setText(status_text)

            # Update pixel crop window if it's open
            self._update_pixel_crop_window()

    def _on_path_clicked(self, event) -> None:
        """Handle path label click - open Finder and highlight file"""
        if self.current_file_path:
            import subprocess
            import sys
            try:
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', '-R', self.current_file_path])
                elif sys.platform == 'win32':  # Windows
                    subprocess.run(['explorer', '/select,', self.current_file_path])
                else:  # Linux
                    subprocess.run(['xdg-open', str(Path(self.current_file_path).parent)])
            except Exception as e:
                print(f"Error opening file location: {e}")

    def _on_find_bad_pixels(self) -> None:
        """Handle Find button - identify bad pixels above threshold"""
        if self.current_raw_data is None:
            self.threshold_field.setText("N/A")
            self.bad_pixel_count_field.setText("0")
            self.bad_pixels_table.setRowCount(0)
            return

        try:
            # Get sigma value
            sigma = self.sigma_spinbox.value()

            # Use original data for finding bad pixels
            raw_data = self.current_raw_data_original if self.current_raw_data_original is not None else self.current_raw_data
            mean_val = float(np.mean(raw_data))
            std_val = float(np.std(raw_data))
            threshold = mean_val + sigma * std_val

            # Find bad pixels (values > threshold)
            bad_mask = raw_data > threshold
            bad_coords = np.argwhere(bad_mask)  # Returns array of [y, x] coordinates
            bad_values = raw_data[bad_mask]

            # Store bad pixel coordinates for removal
            self.current_bad_pixels = bad_coords

            # Update threshold field
            self.threshold_field.setText(f"{threshold:.2f}")

            # Calculate total pixels and percentage
            total_pixels = raw_data.shape[0] * raw_data.shape[1]
            bad_pixel_percentage = (len(bad_coords) / total_pixels) * 100 if total_pixels > 0 else 0

            # Calculate expected number for normal distribution
            from scipy.stats import norm
            probability = 1 - norm.cdf(sigma)  # Right tail probability
            expected_bad_pixels = total_pixels * probability
            expected_percentage = (expected_bad_pixels / total_pixels) * 100 if total_pixels > 0 else 0

            # Update count field with percentage
            self.bad_pixel_count_field.setText(f"{len(bad_coords)} ({bad_pixel_percentage:.3f}%)")

            # Update expected field
            self.expected_count_field.setText(f"{expected_bad_pixels:.1f} ({expected_percentage:.3f}%)")

            # Clear and populate table
            self.bad_pixels_table.setRowCount(0)

            if len(bad_coords) > 0:
                # Sort by value (highest first)
                sorted_indices = np.argsort(bad_values)[::-1]

                # Show up to 1000 pixels in table
                max_display = min(1000, len(bad_coords))
                self.bad_pixels_table.setRowCount(max_display)

                for i in range(max_display):
                    idx = sorted_indices[i]
                    y, x = bad_coords[idx]
                    value = bad_values[idx]

                    # Add row to table
                    self.bad_pixels_table.setItem(i, 0, QTableWidgetItem(str(y)))
                    self.bad_pixels_table.setItem(i, 1, QTableWidgetItem(str(x)))
                    self.bad_pixels_table.setItem(i, 2, QTableWidgetItem(str(value)))

            print(f"Bad pixel search: {len(bad_coords)} pixels found above threshold {threshold:.2f}")

            # If remove bad pixels is checked, trigger re-render
            if self.remove_bad_pixels_checkbox.isChecked():
                self._on_scaling_changed(0)

        except Exception as e:
            self.threshold_field.setText("Error")
            self.bad_pixel_count_field.setText("0")
            print(f"Error in bad pixel search: {e}")
            import traceback
            traceback.print_exc()

    def _remove_bad_pixels(self, raw_data: np.ndarray, bad_coords: np.ndarray) -> np.ndarray:
        """
        Remove bad pixels by replacing with mean of neighbors.

        Args:
            raw_data: Raw image data
            bad_coords: Array of [y, x] coordinates of bad pixels

        Returns:
            Cleaned image data
        """
        cleaned_data = raw_data.copy()
        height, width = raw_data.shape

        for coord in bad_coords:
            y, x = coord

            # Find valid neighbor positions
            neighbors = []
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue  # Skip the center pixel itself

                    ny, nx = y + dy, x + dx

                    # Check if neighbor is within image bounds
                    if 0 <= ny < height and 0 <= nx < width:
                        neighbors.append(raw_data[ny, nx])

            # Replace bad pixel with mean of neighbors
            if len(neighbors) > 0:
                cleaned_data[y, x] = int(np.mean(neighbors))

        return cleaned_data

    def _update_pixel_crop_window(self) -> None:
        """Update pixel crop window if it's open and has data"""
        if (self.pixel_crop_window is not None and
            self.pixel_crop_window.isVisible() and
            self.pixel_crop_window.current_raw_data is not None):

            # Get current scaling settings
            auto_scale = self.auto_scale_checkbox.isChecked()
            log_view = self.log_view_checkbox.isChecked()

            # Refresh the crop window with new scaling
            self.pixel_crop_window.update_crop(
                self.pixel_crop_window.current_raw_data,
                self.pixel_crop_window.current_y,
                self.pixel_crop_window.current_x,
                self.pixel_crop_window.current_value,
                auto_scale,
                log_view
            )
            print(f"Updated pixel crop window with Auto Scale={auto_scale}, Log View={log_view}")

    def _on_bad_pixel_clicked(self, row: int, column: int) -> None:
        """Handle bad pixel table click - show 32x32 crop around pixel"""
        if self.current_raw_data is None:
            return

        try:
            # Get pixel coordinates and value from table
            y = int(self.bad_pixels_table.item(row, 0).text())
            x = int(self.bad_pixels_table.item(row, 1).text())
            value = int(self.bad_pixels_table.item(row, 2).text())

            # Create pixel crop window if it doesn't exist
            if self.pixel_crop_window is None:
                self.pixel_crop_window = PixelCropWindow(self)

            # Get current scaling settings
            auto_scale = self.auto_scale_checkbox.isChecked()
            log_view = self.log_view_checkbox.isChecked()

            # Update the crop window
            self.pixel_crop_window.update_crop(
                self.current_raw_data, y, x, value,
                auto_scale, log_view
            )

            # Show the window
            self.pixel_crop_window.show()
            self.pixel_crop_window.raise_()
            self.pixel_crop_window.activateWindow()

        except Exception as e:
            print(f"Error showing pixel crop: {e}")
            import traceback
            traceback.print_exc()

    def _on_show_projection(self) -> None:
        """Handle Projection button - show axis projection plots"""
        if self.current_raw_data is None:
            self.status_label.setText("No image data available for projections")
            return

        # Create projection window if it doesn't exist
        if self.projection_window is None:
            from views.histogram_window import HistogramWindow
            self.projection_window = HistogramWindow(self)

        # Update with current data
        filename = Path(self.current_file_path).name if self.current_file_path else ""
        self.projection_window.update_histograms(
            self.current_raw_data, filename,
            file_hash=self.current_file_hash,
            camera_id=self.current_camera_id
        )

        # Show the window
        self.projection_window.show()
        self.projection_window.raise_()
        self.projection_window.activateWindow()

    def resizeEvent(self, event) -> None:
        """Handle window resize - auto-fit if checkbox is checked"""
        super().resizeEvent(event)

        # Auto-fit image if checkbox is checked
        if hasattr(self, 'fit_to_window_checkbox') and self.fit_to_window_checkbox.isChecked():
            if self.pixmap_item.pixmap() and not self.pixmap_item.pixmap().isNull():
                self.graphics_view.fit_to_window()
                self._update_zoom_label()

    def reload_with_crop(self) -> None:
        """Reload current image with updated crop settings from database"""
        if self.current_file_path and self.image_loader_callback:
            try:
                print("Reloading image with updated crop settings...")
                result = self.image_loader_callback(self.current_file_path)

                # Handle different return tuple sizes
                if len(result) == 6:
                    pixmap, display_array, stats, raw_data, file_hash, camera_id = result
                elif len(result) == 4:
                    pixmap, display_array, stats, raw_data = result
                    file_hash = self.current_file_hash
                    camera_id = self.current_camera_id
                else:
                    return

                # Reload the image
                self.load_image(
                    pixmap, display_array, self.current_file_path,
                    stats=stats, raw_data=raw_data,
                    file_hash=file_hash, camera_id=camera_id
                )
            except Exception as e:
                print(f"Error reloading image: {e}")
                import traceback
                traceback.print_exc()

    def clear(self) -> None:
        """Clear the image"""
        self.filename_label.setText("No image loaded")
        self.graphics_scene.clear()
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)
        self.status_label.setText("Ready")
