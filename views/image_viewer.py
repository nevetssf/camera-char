"""
Image viewer widget for displaying raw camera files and TIFFs.
Provides zoom, pan, pixel inspection, and metadata display.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QLabel, QPushButton,
    QGroupBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path

from utils.image_loader import get_image_loader, normalize_for_display


class ZoomableGraphicsView(QGraphicsView):
    """Graphics view with zoom and pan capabilities"""

    pixel_hovered = pyqtSignal(int, int, object)  # x, y, pixel_value

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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for pixel inspection"""
        super().mouseMoveEvent(event)

        if self.current_image is not None:
            # Map to scene coordinates
            scene_pos = self.mapToScene(event.pos())
            x, y = int(scene_pos.x()), int(scene_pos.y())

            # Check if within image bounds
            height, width = self.current_image.shape[:2]
            if 0 <= x < width and 0 <= y < height:
                # Get pixel value
                pixel_value = self.current_image[y, x]
                self.pixel_hovered.emit(x, y, pixel_value)

    def fit_to_window(self) -> None:
        """Fit image to window"""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # Calculate zoom level
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


class ImageViewer(QWidget):
    """Image viewer widget with controls and metadata"""

    image_loaded = pyqtSignal(str)  # Emitted when image is loaded

    def __init__(self):
        """Initialize image viewer"""
        super().__init__()

        self.image_loader = get_image_loader()
        self.current_file_path: Optional[str] = None
        self.current_camera_model: Optional[str] = None

        self._create_ui()

    def _create_ui(self) -> None:
        """Create user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Controls row
        controls_layout = QHBoxLayout()

        self.btn_fit = QPushButton("Fit to Window")
        self.btn_fit.clicked.connect(self._on_fit_to_window)
        controls_layout.addWidget(self.btn_fit)

        self.btn_actual_size = QPushButton("100%")
        self.btn_actual_size.clicked.connect(self._on_actual_size)
        controls_layout.addWidget(self.btn_actual_size)

        self.btn_zoom_in = QPushButton("Zoom In")
        self.btn_zoom_in.clicked.connect(self._on_zoom_in)
        controls_layout.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("Zoom Out")
        self.btn_zoom_out.clicked.connect(self._on_zoom_out)
        controls_layout.addWidget(self.btn_zoom_out)

        self.zoom_label = QLabel("Zoom: 100%")
        controls_layout.addWidget(self.zoom_label)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Graphics view
        self.graphics_view = ZoomableGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)

        layout.addWidget(self.graphics_view, stretch=1)

        # Status bar for pixel info
        self.pixel_info_label = QLabel("Pixel info: (hover over image)")
        layout.addWidget(self.pixel_info_label)

        # Metadata panel (collapsible)
        self.metadata_group = QGroupBox("Metadata")
        metadata_layout = QVBoxLayout()
        self.metadata_group.setLayout(metadata_layout)

        self.metadata_scroll = QScrollArea()
        self.metadata_scroll.setWidgetResizable(True)
        self.metadata_scroll.setMaximumHeight(150)

        self.metadata_label = QLabel("No image loaded")
        self.metadata_label.setWordWrap(True)
        self.metadata_scroll.setWidget(self.metadata_label)

        metadata_layout.addWidget(self.metadata_scroll)
        layout.addWidget(self.metadata_group)

        # Connect signals
        self.graphics_view.pixel_hovered.connect(self._on_pixel_hovered)

    def load_image(self, file_path: str, fast_preview: bool = False,
                  camera_model: Optional[str] = None) -> None:
        """
        Load and display an image.

        Args:
            file_path: Path to image file
            fast_preview: Use fast preview mode
            camera_model: Camera model for crop lookup
        """
        try:
            # Load image using image loader
            image_array = self.image_loader.load_image(
                file_path,
                fast_preview=fast_preview,
                camera_model=camera_model
            )

            # Normalize for display
            display_array = normalize_for_display(image_array)

            # Convert to QPixmap
            pixmap = self._numpy_to_pixmap(display_array)

            # Display in graphics view
            self.pixmap_item.setPixmap(pixmap)
            self.graphics_scene.setSceneRect(QRectF(pixmap.rect()))
            self.graphics_view.set_image(display_array)
            self.graphics_view.fit_to_window()

            # Update zoom label
            self._update_zoom_label()

            # Store current file info
            self.current_file_path = file_path
            self.current_camera_model = camera_model

            # Load and display metadata
            self._load_metadata(file_path)

            # Emit signal
            self.image_loaded.emit(file_path)

        except Exception as e:
            self.metadata_label.setText(f"Error loading image:\n{str(e)}")
            raise

    def _numpy_to_pixmap(self, image_array: np.ndarray) -> QPixmap:
        """
        Convert numpy array to QPixmap.

        Args:
            image_array: Image as numpy array

        Returns:
            QPixmap
        """
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

    def _load_metadata(self, file_path: str) -> None:
        """Load and display metadata"""
        try:
            from models.image_model import ImageModel
            image_model = ImageModel()

            # Get simple metadata (fast)
            metadata = image_model.get_simple_metadata(file_path)

            # Format metadata for display
            metadata_text = "<table>"
            metadata_text += f"<tr><td><b>File:</b></td><td>{metadata.get('file_name', 'N/A')}</td></tr>"
            metadata_text += f"<tr><td><b>Size:</b></td><td>{self._format_file_size(metadata.get('file_size', 0))}</td></tr>"

            if 'width' in metadata and 'height' in metadata:
                metadata_text += f"<tr><td><b>Dimensions:</b></td><td>{metadata['width']} x {metadata['height']}</td></tr>"

            if 'channels' in metadata:
                metadata_text += f"<tr><td><b>Channels:</b></td><td>{metadata['channels']}</td></tr>"

            if self.current_camera_model:
                metadata_text += f"<tr><td><b>Camera:</b></td><td>{self.current_camera_model}</td></tr>"

            metadata_text += "</table>"

            self.metadata_label.setText(metadata_text)

        except Exception as e:
            self.metadata_label.setText(f"Metadata: {Path(file_path).name}")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def _on_fit_to_window(self) -> None:
        """Handle fit to window button"""
        self.graphics_view.fit_to_window()
        self._update_zoom_label()

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

    def _update_zoom_label(self) -> None:
        """Update zoom percentage label"""
        zoom_percent = self.graphics_view.current_zoom * 100
        self.zoom_label.setText(f"Zoom: {zoom_percent:.0f}%")

    def _on_pixel_hovered(self, x: int, y: int, pixel_value: Any) -> None:
        """Handle pixel hover event"""
        if isinstance(pixel_value, np.ndarray):
            # RGB pixel
            if len(pixel_value) == 3:
                r, g, b = pixel_value
                self.pixel_info_label.setText(
                    f"Pixel: ({x}, {y}) | RGB: ({r}, {g}, {b})"
                )
            else:
                self.pixel_info_label.setText(
                    f"Pixel: ({x}, {y}) | Value: {pixel_value}"
                )
        else:
            # Grayscale pixel
            self.pixel_info_label.setText(
                f"Pixel: ({x}, {y}) | Value: {pixel_value}"
            )

    def clear_cache(self) -> None:
        """Clear image cache"""
        self.image_loader.clear_cache()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return self.image_loader.get_cache_stats()
