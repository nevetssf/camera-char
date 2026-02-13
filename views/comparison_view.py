"""
Comparison view for side-by-side image comparison.
Provides synchronized zoom/pan and metadata comparison.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QFileDialog, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Optional, Dict, Any
from pathlib import Path

from views.image_window import ZoomableGraphicsView
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from utils.image_loader import get_image_loader, normalize_for_display
from PyQt6.QtGui import QPixmap, QImage
import numpy as np


class ComparisonView(QWidget):
    """Side-by-side comparison view"""

    def __init__(self):
        """Initialize comparison view"""
        super().__init__()

        self.image_loader = get_image_loader()
        self.left_image_path: Optional[str] = None
        self.right_image_path: Optional[str] = None

        self._create_ui()

    def _create_ui(self) -> None:
        """Create user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        title_label = QLabel("Comparison View")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # File selection controls
        controls_layout = QVBoxLayout()

        # Left image
        left_layout = QHBoxLayout()
        left_label = QLabel("Left:")
        self.left_file_button = QPushButton("Select Left Image...")
        self.left_file_button.clicked.connect(self._on_select_left)
        self.left_file_label = QLabel("No image")
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.left_file_button)
        left_layout.addWidget(self.left_file_label, stretch=1)
        controls_layout.addLayout(left_layout)

        # Right image
        right_layout = QHBoxLayout()
        right_label = QLabel("Right:")
        self.right_file_button = QPushButton("Select Right Image...")
        self.right_file_button.clicked.connect(self._on_select_right)
        self.right_file_label = QLabel("No image")
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.right_file_button)
        right_layout.addWidget(self.right_file_label, stretch=1)
        controls_layout.addLayout(right_layout)

        layout.addLayout(controls_layout)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        self.btn_sync_zoom = QPushButton("Sync Zoom/Pan")
        self.btn_sync_zoom.setCheckable(True)
        self.btn_sync_zoom.setChecked(True)
        zoom_layout.addWidget(self.btn_sync_zoom)

        self.btn_fit = QPushButton("Fit to Window")
        self.btn_fit.clicked.connect(self._on_fit_to_window)
        zoom_layout.addWidget(self.btn_fit)

        zoom_layout.addStretch()
        layout.addLayout(zoom_layout)

        # Image viewers (side by side)
        viewers_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left viewer
        self.left_view = ZoomableGraphicsView()
        self.left_scene = QGraphicsScene()
        self.left_view.setScene(self.left_scene)
        self.left_pixmap_item = QGraphicsPixmapItem()
        self.left_scene.addItem(self.left_pixmap_item)
        viewers_splitter.addWidget(self.left_view)

        # Right viewer
        self.right_view = ZoomableGraphicsView()
        self.right_scene = QGraphicsScene()
        self.right_view.setScene(self.right_scene)
        self.right_pixmap_item = QGraphicsPixmapItem()
        self.right_scene.addItem(self.right_pixmap_item)
        viewers_splitter.addWidget(self.right_view)

        layout.addWidget(viewers_splitter, stretch=1)

        # Metadata comparison table
        metadata_group = QGroupBox("Metadata Comparison")
        metadata_layout = QVBoxLayout()
        metadata_group.setLayout(metadata_layout)

        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(3)
        self.metadata_table.setHorizontalHeaderLabels(["Property", "Left", "Right"])
        self.metadata_table.setMaximumHeight(150)
        metadata_layout.addWidget(self.metadata_table)

        layout.addWidget(metadata_group)

        # Connect zoom sync
        self._setup_zoom_sync()

    def _setup_zoom_sync(self) -> None:
        """Setup synchronized zooming and panning"""
        # Note: This is a simplified version. Full sync would require
        # connecting to the view's transform change signals
        pass

    def _on_select_left(self) -> None:
        """Handle select left image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Left Image",
            "",
            "Image Files (*.dng *.DNG *.erf *.ERF *.tiff *.tif);;All Files (*)"
        )

        if file_path:
            self.load_left_image(file_path)

    def _on_select_right(self) -> None:
        """Handle select right image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Right Image",
            "",
            "Image Files (*.dng *.DNG *.erf *.ERF *.tiff *.tif);;All Files (*)"
        )

        if file_path:
            self.load_right_image(file_path)

    def load_left_image(self, file_path: str, camera_model: Optional[str] = None) -> None:
        """
        Load left image.

        Args:
            file_path: Path to image file
            camera_model: Camera model for crop
        """
        try:
            # Load image
            image_array = self.image_loader.load_image(file_path, camera_model=camera_model)
            display_array = normalize_for_display(image_array)

            # Display
            pixmap = self._numpy_to_pixmap(display_array)
            self.left_pixmap_item.setPixmap(pixmap)
            self.left_scene.setSceneRect(pixmap.rect())
            self.left_view.set_image(display_array)
            self.left_view.fit_to_window()

            # Update label
            self.left_image_path = file_path
            self.left_file_label.setText(Path(file_path).name)

            # Update metadata comparison
            self._update_metadata_comparison()

        except Exception as e:
            self.left_file_label.setText(f"Error: {str(e)}")

    def load_right_image(self, file_path: str, camera_model: Optional[str] = None) -> None:
        """
        Load right image.

        Args:
            file_path: Path to image file
            camera_model: Camera model for crop
        """
        try:
            # Load image
            image_array = self.image_loader.load_image(file_path, camera_model=camera_model)
            display_array = normalize_for_display(image_array)

            # Display
            pixmap = self._numpy_to_pixmap(display_array)
            self.right_pixmap_item.setPixmap(pixmap)
            self.right_scene.setSceneRect(pixmap.rect())
            self.right_view.set_image(display_array)
            self.right_view.fit_to_window()

            # Update label
            self.right_image_path = file_path
            self.right_file_label.setText(Path(file_path).name)

            # Update metadata comparison
            self._update_metadata_comparison()

        except Exception as e:
            self.right_file_label.setText(f"Error: {str(e)}")

    def _numpy_to_pixmap(self, image_array: np.ndarray) -> QPixmap:
        """Convert numpy array to QPixmap"""
        height, width = image_array.shape[:2]

        if len(image_array.shape) == 2:
            # Grayscale
            bytes_per_line = width
            q_image = QImage(
                image_array.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_Grayscale8
            )
        else:
            # RGB
            bytes_per_line = 3 * width
            q_image = QImage(
                image_array.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )

        return QPixmap.fromImage(q_image)

    def _update_metadata_comparison(self) -> None:
        """Update metadata comparison table"""
        if not self.left_image_path and not self.right_image_path:
            return

        from models.image_model import ImageModel
        image_model = ImageModel()

        # Get metadata for both images
        left_metadata = {}
        right_metadata = {}

        if self.left_image_path:
            try:
                left_metadata = image_model.get_simple_metadata(self.left_image_path)
            except Exception:
                pass

        if self.right_image_path:
            try:
                right_metadata = image_model.get_simple_metadata(self.right_image_path)
            except Exception:
                pass

        # Combine keys
        all_keys = set(left_metadata.keys()) | set(right_metadata.keys())
        all_keys = sorted(all_keys)

        # Populate table
        self.metadata_table.setRowCount(len(all_keys))

        for i, key in enumerate(all_keys):
            # Property name
            self.metadata_table.setItem(i, 0, QTableWidgetItem(key))

            # Left value
            left_value = str(left_metadata.get(key, "N/A"))
            if key == 'file_size':
                left_value = self._format_file_size(left_metadata.get(key, 0))
            self.metadata_table.setItem(i, 1, QTableWidgetItem(left_value))

            # Right value
            right_value = str(right_metadata.get(key, "N/A"))
            if key == 'file_size':
                right_value = self._format_file_size(right_metadata.get(key, 0))
            self.metadata_table.setItem(i, 2, QTableWidgetItem(right_value))

        self.metadata_table.resizeColumnsToContents()

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def _on_fit_to_window(self) -> None:
        """Fit both images to window"""
        self.left_view.fit_to_window()
        self.right_view.fit_to_window()

    def clear_left(self) -> None:
        """Clear left image"""
        self.left_scene.clear()
        self.left_pixmap_item = QGraphicsPixmapItem()
        self.left_scene.addItem(self.left_pixmap_item)
        self.left_image_path = None
        self.left_file_label.setText("No image")
        self._update_metadata_comparison()

    def clear_right(self) -> None:
        """Clear right image"""
        self.right_scene.clear()
        self.right_pixmap_item = QGraphicsPixmapItem()
        self.right_scene.addItem(self.right_pixmap_item)
        self.right_image_path = None
        self.right_file_label.setText("No image")
        self._update_metadata_comparison()

    def clear_both(self) -> None:
        """Clear both images"""
        self.clear_left()
        self.clear_right()
