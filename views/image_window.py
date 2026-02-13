"""
Image viewer window - popup window for viewing images with zoom controls.
Persists across image loads and updates dynamically.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent, QFont
import numpy as np
from pathlib import Path
from typing import Optional


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


class ImageWindow(QDialog):
    """Window for displaying images with zoom controls"""

    def __init__(self, parent=None):
        """
        Initialize image window.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Image Viewer")
        self.resize(1200, 800)

        # Don't close on escape
        self.setModal(False)

        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header with filename
        header_layout = QHBoxLayout()
        self.filename_label = QLabel("No image loaded")
        filename_font = QFont()
        filename_font.setPointSize(12)
        filename_font.setBold(True)
        self.filename_label.setFont(filename_font)
        header_layout.addWidget(self.filename_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

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

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.hide)
        controls_layout.addWidget(self.close_button)

        layout.addLayout(controls_layout)

        # Graphics view
        self.graphics_view = ZoomableGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)

        layout.addWidget(self.graphics_view, stretch=1)

        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def load_image(self, pixmap: QPixmap, display_array: np.ndarray, file_path: str) -> None:
        """
        Load and display an image.

        Args:
            pixmap: QPixmap to display
            display_array: Numpy array for pixel inspection
            file_path: Path to the file
        """
        # Update filename
        self.filename_label.setText(f"📷 {Path(file_path).name}")

        # Display in graphics view
        self.pixmap_item.setPixmap(pixmap)
        self.graphics_scene.setSceneRect(QRectF(pixmap.rect()))
        self.graphics_view.set_image(display_array)
        self.graphics_view.fit_to_window()

        # Update zoom label
        self._update_zoom_label()

        # Update status
        height, width = display_array.shape[:2]
        self.status_label.setText(f"Image: {width}x{height} pixels | {Path(file_path).name}")

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

    def clear(self) -> None:
        """Clear the image"""
        self.filename_label.setText("No image loaded")
        self.graphics_scene.clear()
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)
        self.status_label.setText("Ready")
