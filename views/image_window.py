"""
Image viewer window - popup window for viewing images with zoom controls.
Persists across image loads and updates dynamically.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QLabel, QPushButton, QFileDialog,
    QCheckBox, QSpinBox, QTextEdit, QGroupBox, QScrollArea, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QStatusBar,
    QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent, QFont
import numpy as np
from pathlib import Path
from typing import Optional, Callable


class ZoomableGraphicsView(QGraphicsView):
    """Graphics view with zoom and pan capabilities"""

    # Signal emitted when mouse moves over image: (x, y, pixel_value)
    mouse_moved = pyqtSignal(int, int, int)

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
        self.raw_image_data = None  # Store raw pixel data for value lookup

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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move to show pixel coordinates and value"""
        super().mouseMoveEvent(event)

        if self.current_image is not None and self.raw_image_data is not None:
            # Map view coordinates to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Get image coordinates
            x = int(scene_pos.x())
            y = int(scene_pos.y())

            # Check if coordinates are within image bounds
            if 0 <= y < self.raw_image_data.shape[0] and 0 <= x < self.raw_image_data.shape[1]:
                pixel_value = int(self.raw_image_data[y, x])
                self.mouse_moved.emit(x, y, pixel_value)

    def set_image(self, image: np.ndarray, raw_data: np.ndarray = None) -> None:
        """
        Set image to display.

        Args:
            image: Display image array (8-bit)
            raw_data: Raw image data for pixel value lookup
        """
        self.current_image = image
        if raw_data is not None:
            self.raw_image_data = raw_data


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
        self.info_label = QLabel("Click on a leaky pixel to view details")
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
        self.stats_label.setStyleSheet("padding: 5px; border: 1px solid palette(mid);")
        layout.addWidget(self.stats_label)

    def update_crop(self, raw_data: np.ndarray, center_y: int, center_x: int,
                    pixel_value: int, scale_mode: str):
        """
        Update the window with a 32x32 crop around the specified pixel.

        Args:
            raw_data: Full raw image data
            center_y: Y coordinate of center pixel
            center_x: X coordinate of center pixel
            pixel_value: Value of the center pixel
            scale_mode: Scale mode ("Linear", "Log", "Normalization", or "Equalization")
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

        # Apply scaling based on mode
        working_data = crop.astype(np.float32)

        # Calculate stats for Linear mode
        crop_min = np.min(crop)
        crop_max = np.max(crop)

        if scale_mode == "Linear":
            # Linear: map from crop min/max to 0-255
            if crop_max > crop_min:
                display_array = ((working_data - crop_min) / (crop_max - crop_min) * 255.0).astype(np.uint8)
            else:
                display_array = np.zeros_like(crop, dtype=np.uint8)

        elif scale_mode == "Log":
            # Log: apply log transformation, then normalize
            working_data = np.log10(working_data + 1.0)
            max_log = np.log10(65536.0)
            display_array = np.clip(working_data / max_log * 255.0, 0, 255).astype(np.uint8)

        elif scale_mode == "Normalization":
            # Normalization: stretch actual min/max to full 0-255 range
            min_val = np.min(working_data)
            max_val = np.max(working_data)
            if max_val > min_val:
                display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
            else:
                display_array = np.zeros_like(crop, dtype=np.uint8)

        elif scale_mode == "Equalization":
            # Equalization: histogram equalization
            min_val = np.min(working_data)
            max_val = np.max(working_data)
            if max_val > min_val:
                normalized = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
            else:
                normalized = np.zeros_like(crop, dtype=np.uint8)

            # Compute histogram
            hist, _ = np.histogram(normalized.flatten(), bins=256, range=(0, 256))

            # Compute cumulative distribution function (CDF)
            cdf = hist.cumsum()

            # Normalize CDF to range 0-255
            cdf_normalized = ((cdf - cdf.min()) * 255 / (cdf.max() - cdf.min())).astype(np.uint8)

            # Map pixel values through the normalized CDF
            display_array = cdf_normalized[normalized]

        else:
            # Fallback to linear
            if crop_max > crop_min:
                display_array = ((working_data - crop_min) / (crop_max - crop_min) * 255.0).astype(np.uint8)
            else:
                display_array = np.zeros_like(crop, dtype=np.uint8)

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


class HistogramValueWindow(QDialog):
    """Window for displaying histogram of pixel values"""

    def __init__(self, parent=None):
        """Initialize histogram value window"""
        super().__init__(parent)
        self.setWindowTitle("Pixel Value Histogram")
        self.resize(800, 600)
        self.setModal(False)

        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Display Mode:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Actual", "Relative", "Bit"])
        self.mode_combo.setToolTip("Actual: raw values\nRelative: normalized by bit depth (÷2^bits)\nBit: log2 of values")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        controls_layout.addWidget(self.mode_combo)

        controls_layout.addSpacing(20)
        controls_layout.addWidget(QLabel("Bins:"))

        self.bins_combo = QComboBox()
        self.bins_combo.addItems(["50", "100", "200", "500", "1000"])
        self.bins_combo.setCurrentIndex(2)  # Default to 200
        self.bins_combo.setToolTip("Number of bins in histogram")
        self.bins_combo.currentIndexChanged.connect(self._on_mode_changed)
        controls_layout.addWidget(self.bins_combo)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Create matplotlib figure
        import matplotlib
        matplotlib.use('Qt5Agg')
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(1, 1, 1)
        self.figure.tight_layout(pad=3.0)

        # Store data for replotting
        self.raw_data = None
        self.filename = ""
        self.bit_depth = 16

    def update_histogram(self, raw_data: np.ndarray, filename: str = "", bit_depth: int = 16):
        """
        Update histogram with new data.

        Args:
            raw_data: Raw image data (2D numpy array)
            filename: Optional filename for title
            bit_depth: Bit depth of the image
        """
        if raw_data is None or len(raw_data.shape) != 2:
            return

        self.raw_data = raw_data
        self.filename = filename
        self.bit_depth = bit_depth

        self._update_plot()

    def _update_plot(self):
        """Update plot based on current data and mode"""
        if self.raw_data is None:
            return

        self.ax.clear()

        mode = self.mode_combo.currentText()
        bins = int(self.bins_combo.currentText())
        flat_data = self.raw_data.flatten()

        if mode == "Actual":
            # Actual pixel values
            self.ax.hist(flat_data, bins=bins, color='steelblue', edgecolor='black', alpha=0.7)
            self.ax.set_xlabel('Pixel Value')
            self.ax.set_ylabel('Count')
            self.ax.set_title(f'Pixel Value Histogram - Actual\n{self.filename}')

        elif mode == "Relative":
            # Normalize by 2^bit_depth
            divisor = 2 ** self.bit_depth
            relative_data = flat_data / divisor
            self.ax.hist(relative_data, bins=bins, color='steelblue', edgecolor='black', alpha=0.7)
            self.ax.set_xlabel('Relative Value (÷ 2^bits)')
            self.ax.set_ylabel('Count')
            self.ax.set_title(f'Pixel Value Histogram - Relative\n{self.filename}')

        elif mode == "Bit":
            # Log2 of values (filter out zeros to avoid -inf)
            nonzero_data = flat_data[flat_data > 0]
            if len(nonzero_data) > 0:
                log_data = np.log2(nonzero_data)
                self.ax.hist(log_data, bins=bins, color='steelblue', edgecolor='black', alpha=0.7)
                self.ax.set_xlabel('log₂(Pixel Value)')
                self.ax.set_ylabel('Count')
                self.ax.set_title(f'Pixel Value Histogram - Bit\n{self.filename}')
            else:
                self.ax.text(0.5, 0.5, 'No non-zero pixels', ha='center', va='center', transform=self.ax.transAxes)

        self.ax.grid(True, alpha=0.3)
        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

    def _on_mode_changed(self, index: int):
        """Handle mode change - replot histogram"""
        self._update_plot()


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
        self.current_raw_data_original = None  # Original data before leaky pixel removal
        self.current_raw_data_uncropped = None  # Original data before crop (for projections)
        self.current_file_path = None
        self.current_stats = None
        self.current_file_hash = None
        self.current_camera_id = None
        self.current_leaky_pixels = None  # List of (y, x) coordinates of leaky pixels
        self.original_width = None  # Original image width before crop
        self.original_height = None  # Original image height before crop

        # Projection window (created on demand)
        self.projection_window = None

        # Histogram value window (created on demand)
        self.histogram_value_window = None

        # Pixel crop window (created on demand)
        self.pixel_crop_window = None

        # Leaky pixel overlay graphics items
        self.leaky_pixel_markers = []

        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Menu bar
        menu_bar = QMenuBar(self)
        main_layout.setMenuBar(menu_bar)

        # File menu
        file_menu = menu_bar.addMenu("File")
        close_action = file_menu.addAction("Close")
        close_action.triggered.connect(self.hide if not self.standalone else self.close)

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

        # Scale Mode dropdown
        controls_layout.addWidget(QLabel("Scale Mode:"))
        self.scale_mode_combo = QComboBox()
        self.scale_mode_combo.addItems(["Linear", "Log", "Normalization", "Equalization"])
        self.scale_mode_combo.setCurrentIndex(1)  # Log by default
        self.scale_mode_combo.setToolTip("Linear: direct pixel values\nLog: logarithmic scaling for HDR\nNormalization: stretch full range to 0-255\nEqualization: improve contrast via histogram redistribution")
        self.scale_mode_combo.currentIndexChanged.connect(self._on_scaling_changed)
        controls_layout.addWidget(self.scale_mode_combo)

        # Remove Leaky Pixels checkbox
        self.remove_leaky_pixels_checkbox = QCheckBox("Remove Leaky Pixels")
        self.remove_leaky_pixels_checkbox.setChecked(True)  # Checked by default
        self.remove_leaky_pixels_checkbox.setToolTip("Replace leaky pixels with mean of neighbors")
        self.remove_leaky_pixels_checkbox.stateChanged.connect(self._on_scaling_changed)
        controls_layout.addWidget(self.remove_leaky_pixels_checkbox)

        controls_layout.addStretch()

        main_layout.addLayout(controls_layout)

        # Main content area: image on left, leaky pixels panel on right
        content_layout = QHBoxLayout()

        # Left side: image and zoom controls
        left_layout = QVBoxLayout()

        # Graphics view
        self.graphics_view = ZoomableGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)

        # Connect mouse tracking signal
        self.graphics_view.mouse_moved.connect(self._on_mouse_moved)

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

        # Right side: Analysis and Leaky Pixels panels
        right_layout = QVBoxLayout()

        # Analysis panel
        analysis_group = QGroupBox("Analysis")
        analysis_layout = QHBoxLayout()

        # Projection button
        self.btn_projection = QPushButton("Projection")
        self.btn_projection.clicked.connect(self._on_show_projection)
        analysis_layout.addWidget(self.btn_projection)

        # Histogram button
        self.btn_histogram = QPushButton("Histogram")
        self.btn_histogram.clicked.connect(self._on_show_histogram)
        analysis_layout.addWidget(self.btn_histogram)

        analysis_layout.addStretch()
        analysis_group.setLayout(analysis_layout)
        right_layout.addWidget(analysis_group)

        # Leaky Pixels panel
        leaky_pixels_group = QGroupBox("Leaky Pixels")
        leaky_pixels_layout = QVBoxLayout()

        # Sigma and Threshold on same line
        sigma_threshold_layout = QHBoxLayout()
        sigma_threshold_layout.addWidget(QLabel("Sigma:"))
        self.sigma_combo = QComboBox()
        self.sigma_combo.addItems(["6", "9", "12"])
        self.sigma_combo.setCurrentIndex(0)  # 6 by default
        self.sigma_combo.setToolTip("Find pixels > mean + σ × std_dev")
        self.sigma_combo.currentIndexChanged.connect(self._on_find_leaky_pixels)
        sigma_threshold_layout.addWidget(self.sigma_combo)
        sigma_threshold_layout.addSpacing(20)
        sigma_threshold_layout.addWidget(QLabel("Threshold:"))
        self.threshold_label = QLabel("N/A")
        self.threshold_label.setStyleSheet("font-weight: bold;")
        sigma_threshold_layout.addWidget(self.threshold_label)
        sigma_threshold_layout.addStretch()
        leaky_pixels_layout.addLayout(sigma_threshold_layout)

        # Total and Expected on same line
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Total:"))
        self.leaky_pixel_count_label = QLabel("0")
        self.leaky_pixel_count_label.setStyleSheet("font-weight: bold;")
        count_layout.addWidget(self.leaky_pixel_count_label)
        count_layout.addSpacing(20)
        count_layout.addWidget(QLabel("Expected:"))
        self.expected_count_label = QLabel("N/A")
        self.expected_count_label.setStyleSheet("font-weight: bold;")
        self.expected_count_label.setToolTip("Expected leaky pixels for a normal distribution")
        count_layout.addWidget(self.expected_count_label)
        count_layout.addStretch()
        leaky_pixels_layout.addLayout(count_layout)

        # Show leaky pixels dropdown
        show_pixels_layout = QHBoxLayout()
        show_pixels_layout.addWidget(QLabel("Show Leaky Pixels:"))
        self.show_leaky_pixels_combo = QComboBox()
        self.show_leaky_pixels_combo.addItems(["Off", "1x1", "3x3", "5x5", "7x7", "9x9"])
        self.show_leaky_pixels_combo.setCurrentIndex(0)  # Off by default
        self.show_leaky_pixels_combo.setToolTip("Overlay red markers on image at leaky pixel locations")
        self.show_leaky_pixels_combo.currentIndexChanged.connect(self._on_show_leaky_pixels_changed)
        show_pixels_layout.addWidget(self.show_leaky_pixels_combo)
        show_pixels_layout.addStretch()
        leaky_pixels_layout.addLayout(show_pixels_layout)

        # Results table
        self.leaky_pixels_table = QTableWidget()
        self.leaky_pixels_table.setColumnCount(3)
        self.leaky_pixels_table.setHorizontalHeaderLabels(["Row", "Col", "Value"])
        self.leaky_pixels_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.leaky_pixels_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.leaky_pixels_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.leaky_pixels_table.cellClicked.connect(self._on_leaky_pixel_clicked)
        leaky_pixels_layout.addWidget(self.leaky_pixels_table, stretch=1)

        leaky_pixels_group.setLayout(leaky_pixels_layout)
        right_layout.addWidget(leaky_pixels_group, stretch=1)

        # Add right side layout to content
        content_layout.addLayout(right_layout, stretch=1)

        main_layout.addLayout(content_layout, stretch=1)

        # Statistics panel
        stats_layout = QHBoxLayout()

        # Stats display mode dropdown
        self.stats_mode_combo = QComboBox()
        self.stats_mode_combo.addItems(["Actual", "Relative", "Bit"])
        self.stats_mode_combo.setToolTip("Actual: raw values\nRelative: normalized by bit depth (÷2^bits)\nBit: log2 of values")
        self.stats_mode_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.stats_mode_combo.setMaximumWidth(100)  # Limit width to 100 pixels
        self.stats_mode_combo.currentIndexChanged.connect(self._on_stats_mode_changed)
        stats_layout.addWidget(self.stats_mode_combo)

        self.stats_label = QLabel("No image statistics")
        stats_font = QFont("Monospace", 11)
        self.stats_label.setFont(stats_font)
        self.stats_label.setStyleSheet("padding: 8px; border: 1px solid palette(mid);")
        stats_layout.addWidget(self.stats_label)
        main_layout.addLayout(stats_layout)

        # Pixel info label
        self.pixel_info_label = QLabel("Move cursor over image to see pixel values")
        self.pixel_info_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        main_layout.addWidget(self.pixel_info_label)

        # Status bar
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Ready")

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
        # Show loading status
        self.status_bar.showMessage(f"Loading image: {Path(file_path).name}...")

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

        # Store original dimensions and uncropped data (before any cropping)
        if raw_data is not None:
            self.original_height, self.original_width = raw_data.shape
            self.current_raw_data_uncropped = raw_data.copy()  # Save uncropped for projections
        else:
            self.original_width = stats.get('width') if stats else None
            self.original_height = stats.get('height') if stats else None
            self.current_raw_data_uncropped = None

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
                        self.status_bar.showMessage("Applying camera crop...", 1000)
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
                                'width': self.original_width,  # Keep original width
                                'height': self.original_height,  # Keep original height
                                'mean': mean_val,
                                'std': std_val,
                                'min': min_val,
                                'max': max_val,
                                'crop_applied': True,
                                'crop_bounds': f"x[{x_min}:{x_max}], y[{y_min}:{y_max}]",
                                'cropped_width': xdim,
                                'cropped_height': ydim,
                                'original_width': self.original_width,
                                'original_height': self.original_height
                            }
            except Exception as e:
                print(f"Could not apply camera crop: {e}")

        # Store the cropped data as both current and original
        # Original is the base data after crop but before leaky pixel removal
        self.current_raw_data = raw_data
        self.current_raw_data_original = raw_data.copy() if raw_data is not None else None

        # Update filename with full path
        self.filename_label.setText(file_path)

        # Update statistics panel if stats provided
        if stats:
            self.set_statistics(stats)

        # Apply scaling if we have raw data
        if raw_data is not None and stats is not None:
            scale_mode = self.scale_mode_combo.currentText()
            print(f"Applying scaling on load: Scale Mode={scale_mode}")

            # Start with raw data
            working_data = raw_data.astype(np.float32)

            # Apply scale mode transformation
            if scale_mode == "Linear":
                # Linear: map from stats min/max to 0-255
                min_val = stats.get('min', 0)
                max_val = stats.get('max', 65535)
                if max_val > min_val:
                    display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    display_array = np.zeros_like(raw_data, dtype=np.uint8)

            elif scale_mode == "Log":
                # Log: apply log transformation, then map to 0-255
                working_data = np.log10(working_data + 1.0)
                max_log = np.log10(65536.0)
                display_array = np.clip(working_data / max_log * 255.0, 0, 255).astype(np.uint8)

            elif scale_mode == "Normalization":
                # Normalization: stretch actual min/max to full 0-255 range
                min_val = np.min(working_data)
                max_val = np.max(working_data)
                if max_val > min_val:
                    display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    display_array = np.zeros_like(raw_data, dtype=np.uint8)

            elif scale_mode == "Equalization":
                # Equalization: redistribute intensity values via histogram equalization
                # First normalize to 0-255 range for histogram
                min_val = np.min(working_data)
                max_val = np.max(working_data)
                if max_val > min_val:
                    normalized = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    normalized = np.zeros_like(raw_data, dtype=np.uint8)

                # Compute histogram
                hist, _ = np.histogram(normalized.flatten(), bins=256, range=(0, 256))

                # Compute cumulative distribution function (CDF)
                cdf = hist.cumsum()

                # Normalize CDF to range 0-255
                cdf_normalized = ((cdf - cdf.min()) * 255 / (cdf.max() - cdf.min())).astype(np.uint8)

                # Map pixel values through the normalized CDF
                display_array = cdf_normalized[normalized]

            else:
                # Fallback to linear
                display_array = (working_data / 65535.0 * 255.0).astype(np.uint8)

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
        self.graphics_view.set_image(display_array, raw_data)

        # Update status
        if stats:
            self.status_bar.showMessage(f"Image loaded: {stats['width']}×{stats['height']} pixels", 2000)
        else:
            self.status_bar.showMessage("Image loaded", 2000)

        # Auto-update projection if window is open
        if self.projection_window is not None and self.projection_window.isVisible():
            filename = Path(file_path).name
            # Use uncropped data for projections so sliders work with original coordinates
            projection_data = self.current_raw_data_uncropped if self.current_raw_data_uncropped is not None else self.current_raw_data
            self.projection_window.update_histograms(
                projection_data, filename,
                file_hash=self.current_file_hash,
                camera_id=self.current_camera_id
            )

        # Auto-update histogram if window is open
        if self.histogram_value_window is not None and self.histogram_value_window.isVisible():
            filename = Path(file_path).name
            bit_depth = stats.get('bit_depth', 16) if stats else 16
            self.histogram_value_window.update_histogram(
                self.current_raw_data, filename, bit_depth
            )

        # Fit to window if checkbox is checked
        # Use QTimer to ensure window is fully sized before fitting
        if self.fit_to_window_checkbox.isChecked():
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._delayed_fit_to_window)

        # Update zoom label
        self._update_zoom_label()

        # Automatically find leaky pixels
        self._on_find_leaky_pixels()

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
        # Store stats for reformatting when mode changes
        self.current_stats = stats

        # Format and display
        self._update_stats_display()

    def _update_stats_display(self) -> None:
        """Update stats label based on current stats and display mode"""
        if not self.current_stats:
            return

        stats = self.current_stats
        mode = self.stats_mode_combo.currentText()
        bit_depth = stats.get('bit_depth', 16)

        # Format values based on mode
        if mode == "Actual":
            mean_str = f"{stats.get('mean', 0):.2f}"
            std_str = f"{stats.get('std', 0):.2f}"
            min_str = f"{stats.get('min', 0)}"
            max_str = f"{stats.get('max', 0)}"
        elif mode == "Relative":
            # Normalize by 2^bit_depth
            divisor = 2 ** bit_depth
            mean_str = f"{stats.get('mean', 0) / divisor:.6f}"
            std_str = f"{stats.get('std', 0) / divisor:.6f}"
            min_str = f"{stats.get('min', 0) / divisor:.6f}"
            max_str = f"{stats.get('max', 0) / divisor:.6f}"
        elif mode == "Bit":
            # Show log2 of values
            import math
            mean_val = stats.get('mean', 0)
            std_val = stats.get('std', 0)
            min_val = stats.get('min', 0)
            max_val = stats.get('max', 0)

            mean_str = f"{math.log2(mean_val):.2f}" if mean_val > 0 else "-inf"
            std_str = f"{math.log2(std_val):.2f}" if std_val > 0 else "-inf"
            min_str = f"{math.log2(min_val):.2f}" if min_val > 0 else "-inf"
            max_str = f"{math.log2(max_val):.2f}" if max_val > 0 else "-inf"
        else:
            # Fallback to actual
            mean_str = f"{stats.get('mean', 0):.2f}"
            std_str = f"{stats.get('std', 0):.2f}"
            min_str = f"{stats.get('min', 0)}"
            max_str = f"{stats.get('max', 0)}"

        stats_text = (
            f"Bit Depth: {bit_depth}-bit  |  "
            f"Dimensions: {stats.get('width', 0)} × {stats.get('height', 0)}  |  "
            f"Mean: {mean_str}  |  "
            f"Std Dev: {std_str}  |  "
            f"Min: {min_str}  |  "
            f"Max: {max_str}"
        )

        # Add crop indicator if crop was applied
        if stats.get('crop_applied'):
            cropped_w = stats.get('cropped_width')
            cropped_h = stats.get('cropped_height')
            if cropped_w and cropped_h:
                stats_text += f"  |  ⚠️ CROP ACTIVE: {stats.get('crop_bounds', '')} → {cropped_w}×{cropped_h}"
            else:
                stats_text += f"  |  ⚠️ CROP ACTIVE: {stats.get('crop_bounds', '')}"

        self.stats_label.setText(stats_text)

    def _on_stats_mode_changed(self, index: int) -> None:
        """Handle stats display mode change - reformat current stats"""
        self._update_stats_display()

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
                self.status_bar.showMessage(f"Error loading image: {str(e)}")
                print(f"Error loading {file_path}: {e}")
                import traceback
                traceback.print_exc()

    def _update_zoom_label(self) -> None:
        """Update zoom percentage label"""
        zoom_percent = self.graphics_view.current_zoom * 100
        self.zoom_label.setText(f"Zoom: {zoom_percent:.0f}%")

    def _on_scaling_changed(self, state: int) -> None:
        """Handle scaling changes - re-render image with new scaling"""
        if self.current_raw_data is not None and self.current_stats is not None:
            scale_mode = self.scale_mode_combo.currentText()
            remove_leaky_pixels = self.remove_leaky_pixels_checkbox.isChecked()
            print(f"Scaling changed: Scale Mode={scale_mode}, Remove Leaky Pixels={remove_leaky_pixels}")

            # Use cleaned data if remove leaky pixels is checked and leaky pixels have been found
            if remove_leaky_pixels and self.current_leaky_pixels is not None and len(self.current_leaky_pixels) > 0:
                source_data = self.current_raw_data_original if self.current_raw_data_original is not None else self.current_raw_data
                raw_data = self._remove_leaky_pixels(source_data, self.current_leaky_pixels)
                print(f"  Removed {len(self.current_leaky_pixels)} leaky pixels")
            else:
                raw_data = self.current_raw_data_original if self.current_raw_data_original is not None else self.current_raw_data

            ydim, xdim = raw_data.shape

            # Start with raw data
            working_data = raw_data.astype(np.float32)

            # Apply scaling based on mode
            if scale_mode == "Linear":
                # Linear: map from stats min/max to 0-255
                min_val = self.current_stats.get('min', 0)
                max_val = self.current_stats.get('max', 65535)
                if max_val > min_val:
                    display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    display_array = np.zeros_like(raw_data, dtype=np.uint8)

            elif scale_mode == "Log":
                # Log: apply log transformation, then map to 0-255
                print(f"  Applying log scaling")
                working_data = np.log10(working_data + 1.0)
                max_log = np.log10(65536.0)
                display_array = np.clip(working_data / max_log * 255.0, 0, 255).astype(np.uint8)

            elif scale_mode == "Normalization":
                # Normalization: stretch actual min/max to full 0-255 range
                min_val = np.min(working_data)
                max_val = np.max(working_data)
                print(f"  Normalizing from {min_val:.2f} to {max_val:.2f}")
                if max_val > min_val:
                    display_array = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    display_array = np.zeros_like(raw_data, dtype=np.uint8)

            elif scale_mode == "Equalization":
                # Equalization: redistribute intensity values via histogram equalization
                print(f"  Applying histogram equalization")
                min_val = np.min(working_data)
                max_val = np.max(working_data)
                print(f"  Input range: {min_val:.2f} to {max_val:.2f}")
                if max_val > min_val:
                    normalized = ((working_data - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                else:
                    normalized = np.zeros_like(raw_data, dtype=np.uint8)

                # Compute histogram
                hist, _ = np.histogram(normalized.flatten(), bins=256, range=(0, 256))

                # Compute cumulative distribution function (CDF)
                cdf = hist.cumsum()

                # Normalize CDF to range 0-255
                cdf_normalized = ((cdf - cdf.min()) * 255 / (cdf.max() - cdf.min())).astype(np.uint8)

                # Map pixel values through the normalized CDF
                display_array = cdf_normalized[normalized]
                print(f"  Histogram equalized: CDF range {cdf.min()} to {cdf.max()}")

            else:
                # Fallback: use linear mode
                min_val = self.current_stats.get('min', 0)
                max_val = self.current_stats.get('max', 65535)
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
            self.graphics_view.set_image(display_array, raw_data)

            # Update status
            self.status_bar.showMessage(f"Scaling applied: {scale_mode}", 2000)  # Show for 2 seconds

            # Update pixel crop window if it's open
            self._update_pixel_crop_window()

    def _on_mouse_moved(self, x: int, y: int, pixel_value: int) -> None:
        """Handle mouse movement over image - display pixel coordinates and value"""
        self.pixel_info_label.setText(f"x={x}, y={y}, value={pixel_value}")

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

    def _on_find_leaky_pixels(self) -> None:
        """Handle Find button - identify leaky pixels above threshold"""
        if self.current_raw_data is None:
            self.threshold_label.setText("N/A")
            self.leaky_pixel_count_label.setText("0")
            self.leaky_pixels_table.setRowCount(0)
            return

        # Show finding status
        self.status_bar.showMessage("Finding leaky pixels...")

        try:
            # Get sigma value from combo box
            sigma = int(self.sigma_combo.currentText())

            # Use original data for finding leaky pixels
            raw_data = self.current_raw_data_original if self.current_raw_data_original is not None else self.current_raw_data
            mean_val = float(np.mean(raw_data))
            std_val = float(np.std(raw_data))
            threshold = mean_val + sigma * std_val

            # Find leaky pixels (values > threshold)
            bad_mask = raw_data > threshold
            bad_coords = np.argwhere(bad_mask)  # Returns array of [y, x] coordinates
            bad_values = raw_data[bad_mask]

            # Store leaky pixel coordinates for removal
            self.current_leaky_pixels = bad_coords

            # Update threshold label
            self.threshold_label.setText(f"{threshold:.2f}")

            # Calculate total pixels and percentage
            total_pixels = raw_data.shape[0] * raw_data.shape[1]
            leaky_pixel_percentage = (len(bad_coords) / total_pixels) * 100 if total_pixels > 0 else 0

            # Calculate expected number for normal distribution
            from scipy.stats import norm
            probability = 1 - norm.cdf(sigma)  # Right tail probability
            expected_leaky_pixels = total_pixels * probability
            expected_percentage = (expected_leaky_pixels / total_pixels) * 100 if total_pixels > 0 else 0

            # Update count label with percentage
            self.leaky_pixel_count_label.setText(f"{len(bad_coords)} ({leaky_pixel_percentage:.3f}%)")

            # Update expected label
            self.expected_count_label.setText(f"{expected_leaky_pixels:.1f} ({expected_percentage:.3f}%)")

            # Clear and populate table
            self.leaky_pixels_table.setRowCount(0)

            if len(bad_coords) > 0:
                # Sort by value (highest first)
                sorted_indices = np.argsort(bad_values)[::-1]

                # Show up to 1000 pixels in table
                max_display = min(1000, len(bad_coords))
                self.leaky_pixels_table.setRowCount(max_display)

                for i in range(max_display):
                    idx = sorted_indices[i]
                    y, x = bad_coords[idx]
                    value = bad_values[idx]

                    # Add row to table
                    self.leaky_pixels_table.setItem(i, 0, QTableWidgetItem(str(y)))
                    self.leaky_pixels_table.setItem(i, 1, QTableWidgetItem(str(x)))
                    self.leaky_pixels_table.setItem(i, 2, QTableWidgetItem(str(value)))

            print(f"Leaky pixel search: {len(bad_coords)} pixels found above threshold {threshold:.2f}")

            # Update status
            self.status_bar.showMessage(f"Found {len(bad_coords)} leaky pixels", 2000)

            # Update leaky pixel markers if show is not Off
            if self.show_leaky_pixels_combo.currentText() != "Off":
                self._remove_leaky_pixel_markers()
                self._add_leaky_pixel_markers()

            # If remove leaky pixels is checked, trigger re-render
            if self.remove_leaky_pixels_checkbox.isChecked():
                self._on_scaling_changed(0)

        except Exception as e:
            self.threshold_label.setText("Error")
            self.leaky_pixel_count_label.setText("0")
            print(f"Error in leaky pixel search: {e}")
            import traceback
            traceback.print_exc()

    def _remove_leaky_pixels(self, raw_data: np.ndarray, bad_coords: np.ndarray) -> np.ndarray:
        """
        Remove leaky pixels by replacing with mean of neighbors.

        Args:
            raw_data: Raw image data
            bad_coords: Array of [y, x] coordinates of leaky pixels

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

            # Replace leaky pixel with mean of neighbors
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
            scale_mode = self.scale_mode_combo.currentText()

            # Refresh the crop window with new scaling
            self.pixel_crop_window.update_crop(
                self.pixel_crop_window.current_raw_data,
                self.pixel_crop_window.current_y,
                self.pixel_crop_window.current_x,
                self.pixel_crop_window.current_value,
                auto_scale,
                scale_mode
            )
            print(f"Updated pixel crop window with Auto Scale={auto_scale}, Scale Mode={scale_mode}")

    def _on_leaky_pixel_clicked(self, row: int, column: int) -> None:
        """Handle leaky pixel table click - show 32x32 crop around pixel"""
        if self.current_raw_data is None:
            return

        try:
            # Get pixel coordinates and value from table
            y = int(self.leaky_pixels_table.item(row, 0).text())
            x = int(self.leaky_pixels_table.item(row, 1).text())
            value = int(self.leaky_pixels_table.item(row, 2).text())

            # Create pixel crop window if it doesn't exist
            if self.pixel_crop_window is None:
                self.pixel_crop_window = PixelCropWindow(self)

            # Get current scaling settings
            scale_mode = self.scale_mode_combo.currentText()

            # Update the crop window
            self.pixel_crop_window.update_crop(
                self.current_raw_data, y, x, value,
                scale_mode
            )

            # Show the window
            self.pixel_crop_window.show()
            self.pixel_crop_window.raise_()
            self.pixel_crop_window.activateWindow()

        except Exception as e:
            print(f"Error showing pixel crop: {e}")
            import traceback
            traceback.print_exc()

    def _on_show_leaky_pixels_changed(self, index: int) -> None:
        """Handle Show Leaky Pixels dropdown - overlay red markers on image"""
        # Remove existing markers
        self._remove_leaky_pixel_markers()

        # Add new markers if not Off
        if self.show_leaky_pixels_combo.currentText() != "Off":
            self._add_leaky_pixel_markers()

    def _add_leaky_pixel_markers(self) -> None:
        """Add red markers for each leaky pixel based on selected size"""
        if self.current_leaky_pixels is None or len(self.current_leaky_pixels) == 0:
            return

        from PyQt6.QtGui import QPen, QBrush, QColor

        # Get marker size from dropdown
        size_text = self.show_leaky_pixels_combo.currentText()
        if size_text == "Off":
            return

        # Parse size (e.g., "1x1" -> 1, "3x3" -> 3, "5x5" -> 5)
        size = int(size_text.split('x')[0])

        # Create red pen and brush
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(0)  # Cosmetic pen (always 1 pixel wide regardless of zoom)
        brush = QBrush(QColor(255, 0, 0, 180))  # Semi-transparent red

        # Add marker for each leaky pixel
        for y, x in self.current_leaky_pixels:
            if size == 1:
                # Single pixel: draw a 1x1 rectangle
                rect = self.graphics_scene.addRect(x, y, 1, 1, pen, brush)
                rect.setZValue(100)
                self.leaky_pixel_markers.append(rect)
            else:
                # Multi-pixel: draw a square centered on the pixel
                half_size = size // 2
                rect = self.graphics_scene.addRect(
                    x - half_size, y - half_size, size, size, pen, brush
                )
                rect.setZValue(100)
                self.leaky_pixel_markers.append(rect)

        print(f"Added {len(self.leaky_pixel_markers)} leaky pixel markers ({size_text})")

    def _remove_leaky_pixel_markers(self) -> None:
        """Remove all leaky pixel markers from the scene"""
        for marker in self.leaky_pixel_markers:
            self.graphics_scene.removeItem(marker)
        self.leaky_pixel_markers.clear()
        print("Removed all leaky pixel markers")

    def _on_show_projection(self) -> None:
        """Handle Projection button - show axis projection plots"""
        if self.current_raw_data is None:
            self.status_bar.showMessage("No image data available for projections", 3000)
            return

        # Create projection window if it doesn't exist
        if self.projection_window is None:
            from views.histogram_window import HistogramWindow
            self.projection_window = HistogramWindow(self)

        # Update with current data
        filename = Path(self.current_file_path).name if self.current_file_path else ""
        # Use uncropped data for projections so sliders work with original coordinates
        projection_data = self.current_raw_data_uncropped if self.current_raw_data_uncropped is not None else self.current_raw_data
        self.projection_window.update_histograms(
            projection_data, filename,
            file_hash=self.current_file_hash,
            camera_id=self.current_camera_id
        )

        # Show the window
        self.projection_window.show()
        self.projection_window.raise_()
        self.projection_window.activateWindow()

    def _on_show_histogram(self) -> None:
        """Handle Histogram button - show pixel value histogram"""
        if self.current_raw_data is None:
            self.status_bar.showMessage("No image data available for histogram", 3000)
            return

        # Create histogram window if it doesn't exist
        if self.histogram_value_window is None:
            self.histogram_value_window = HistogramValueWindow(self)

        # Update with current data (use cropped data for histogram)
        filename = Path(self.current_file_path).name if self.current_file_path else ""
        bit_depth = self.current_stats.get('bit_depth', 16) if self.current_stats else 16
        self.histogram_value_window.update_histogram(
            self.current_raw_data, filename, bit_depth
        )

        # Show the window
        self.histogram_value_window.show()
        self.histogram_value_window.raise_()
        self.histogram_value_window.activateWindow()

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
        self.status_bar.showMessage("Ready")
