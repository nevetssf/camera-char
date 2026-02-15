"""
Projection Window - Shows X and Y axis projection plots of raw image data.
A projection is the mean of pixel values along each axis (dimension).
X projection: mean along Y axis (vertical mean) -> horizontal profile
Y projection: mean along X axis (horizontal mean) -> vertical profile
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QSpinBox
from PyQt6.QtCore import Qt
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from typing import Optional


class HistogramWindow(QDialog):
    """Window for displaying X and Y axis projections"""

    def __init__(self, parent=None):
        """Initialize projection window"""
        super().__init__(parent)
        self.setWindowTitle("Axis Projections")
        self.resize(800, 700)
        self.setModal(False)

        # Store full projection data for range limiting
        self.x_projection_full = None
        self.y_projection_full = None

        # Store file hash and camera ID for database updates
        self.current_file_hash = None
        self.current_camera_id = None

        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create matplotlib figure with two subplots
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Create subplots
        self.ax_x = self.figure.add_subplot(2, 1, 1)
        self.ax_y = self.figure.add_subplot(2, 1, 2)

        self.figure.tight_layout(pad=3.0)

        # Add X-axis range sliders
        x_slider_layout = QHBoxLayout()
        x_slider_layout.addWidget(QLabel("X Range:"))

        self.x_min_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_min_slider.setMinimum(0)
        self.x_min_slider.setMaximum(1000)
        self.x_min_slider.setValue(0)
        self.x_min_slider.setSingleStep(1)  # Fine adjustment with arrow keys
        self.x_min_slider.setPageStep(10)  # Larger jump with Page Up/Down
        self.x_min_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Allow click to focus
        self.x_min_slider.valueChanged.connect(self._on_x_range_changed)
        x_slider_layout.addWidget(QLabel("Min:"))
        x_slider_layout.addWidget(self.x_min_slider)

        self.x_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_max_slider.setMinimum(0)
        self.x_max_slider.setMaximum(1000)
        self.x_max_slider.setValue(1000)
        self.x_max_slider.setSingleStep(1)  # Fine adjustment with arrow keys
        self.x_max_slider.setPageStep(10)  # Larger jump with Page Up/Down
        self.x_max_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Allow click to focus
        self.x_max_slider.valueChanged.connect(self._on_x_range_changed)
        x_slider_layout.addWidget(QLabel("Max:"))
        x_slider_layout.addWidget(self.x_max_slider)

        self.x_range_label = QLabel("0 - 1000")
        x_slider_layout.addWidget(self.x_range_label)
        layout.addLayout(x_slider_layout)

        # Add Y-axis range sliders
        y_slider_layout = QHBoxLayout()
        y_slider_layout.addWidget(QLabel("Y Range:"))

        self.y_min_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_min_slider.setMinimum(0)
        self.y_min_slider.setMaximum(1000)
        self.y_min_slider.setValue(0)
        self.y_min_slider.setSingleStep(1)  # Fine adjustment with arrow keys
        self.y_min_slider.setPageStep(10)  # Larger jump with Page Up/Down
        self.y_min_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Allow click to focus
        self.y_min_slider.valueChanged.connect(self._on_y_range_changed)
        y_slider_layout.addWidget(QLabel("Min:"))
        y_slider_layout.addWidget(self.y_min_slider)

        self.y_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_max_slider.setMinimum(0)
        self.y_max_slider.setMaximum(1000)
        self.y_max_slider.setValue(1000)
        self.y_max_slider.setSingleStep(1)  # Fine adjustment with arrow keys
        self.y_max_slider.setPageStep(10)  # Larger jump with Page Up/Down
        self.y_max_slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Allow click to focus
        self.y_max_slider.valueChanged.connect(self._on_y_range_changed)
        y_slider_layout.addWidget(QLabel("Max:"))
        y_slider_layout.addWidget(self.y_max_slider)

        self.y_range_label = QLabel("0 - 1000")
        y_slider_layout.addWidget(self.y_range_label)
        layout.addLayout(y_slider_layout)

        # Apply button
        apply_layout = QHBoxLayout()
        apply_layout.addStretch()
        self.apply_button = QPushButton("Apply")
        self.apply_button.setToolTip("Save projection range settings for this camera")
        self.apply_button.clicked.connect(self._on_apply)
        apply_layout.addWidget(self.apply_button)
        layout.addLayout(apply_layout)

    def update_histograms(self, raw_data: np.ndarray, filename: str = "",
                         file_hash: Optional[str] = None, camera_id: Optional[int] = None):
        """
        Update projection plots with new data.

        Calculates axis projections by summing pixel values along each dimension.

        Args:
            raw_data: Raw image data (2D numpy array) - should be uncropped original data
            filename: Optional filename for title
            file_hash: File hash for database lookup
            camera_id: Camera ID for loading/saving attributes
        """
        if raw_data is None or len(raw_data.shape) != 2:
            return

        # Store file hash and camera ID
        self.current_file_hash = file_hash
        self.current_camera_id = camera_id

        # Calculate projections from the data (should be uncropped original)
        # Mean along axis 0 (rows) -> gives values for each column (X profile)
        self.x_projection_full = np.mean(raw_data.astype(np.float64), axis=0)

        # Mean along axis 1 (columns) -> gives values for each row (Y profile)
        self.y_projection_full = np.mean(raw_data.astype(np.float64), axis=1)

        self.filename = filename

        # Slider ranges match the data dimensions (original uncropped dimensions)
        slider_width = len(self.x_projection_full)
        slider_height = len(self.y_projection_full)

        # Block signals while setting up sliders to prevent premature _update_plots calls
        self.x_min_slider.blockSignals(True)
        self.x_max_slider.blockSignals(True)
        self.y_min_slider.blockSignals(True)
        self.y_max_slider.blockSignals(True)

        # Set up sliders for the new data using original dimensions
        # Min sliders: 0 to 120
        self.x_min_slider.setMinimum(0)
        self.x_min_slider.setMaximum(min(120, slider_width - 1))

        # Max sliders: (length - 120) to length
        self.x_max_slider.setMinimum(max(0, slider_width - 120))
        self.x_max_slider.setMaximum(slider_width - 1)

        # Min sliders: 0 to 120
        self.y_min_slider.setMinimum(0)
        self.y_min_slider.setMaximum(min(120, slider_height - 1))

        # Max sliders: (length - 120) to length
        self.y_max_slider.setMinimum(max(0, slider_height - 120))
        self.y_max_slider.setMaximum(slider_height - 1)

        # Load saved camera attributes if available
        saved_attrs = None
        if camera_id is not None:
            try:
                from utils.db_manager import get_db_manager
                db = get_db_manager()
                saved_attrs = db.get_camera_attributes(camera_id)
                print(f"Loaded camera attributes: {saved_attrs}")
            except Exception as e:
                print(f"Could not load camera attributes: {e}")

        # Apply saved attributes or defaults
        # Validate that saved values are within original image dimensions
        if saved_attrs:
            x_min = saved_attrs.get('x_min')
            x_max = saved_attrs.get('x_max')
            y_min = saved_attrs.get('y_min')
            y_max = saved_attrs.get('y_max')

            # Validate X bounds against original dimensions
            if x_min is not None and 0 <= x_min < slider_width:
                self.x_min_slider.setValue(x_min)
            else:
                self.x_min_slider.setValue(0)

            if x_max is not None and 0 <= x_max < slider_width:
                self.x_max_slider.setValue(x_max)
            else:
                self.x_max_slider.setValue(slider_width - 1)

            # Validate Y bounds against original dimensions
            if y_min is not None and 0 <= y_min < slider_height:
                self.y_min_slider.setValue(y_min)
            else:
                self.y_min_slider.setValue(0)

            if y_max is not None and 0 <= y_max < slider_height:
                self.y_max_slider.setValue(y_max)
            else:
                self.y_max_slider.setValue(slider_height - 1)
        else:
            # Default values - use original dimensions
            self.x_min_slider.setValue(0)
            self.x_max_slider.setValue(slider_width - 1)
            self.y_min_slider.setValue(0)
            self.y_max_slider.setValue(slider_height - 1)

        # Unblock signals now that all sliders are configured
        self.x_min_slider.blockSignals(False)
        self.x_max_slider.blockSignals(False)
        self.y_min_slider.blockSignals(False)
        self.y_max_slider.blockSignals(False)

        # Initial plot with full range
        self._update_plots()

        print(f"Axis projections updated:")
        print(f"  X projection: {len(self.x_projection_full)} points, range {self.x_projection_full.min():.0f} to {self.x_projection_full.max():.0f}")
        print(f"  Y projection: {len(self.y_projection_full)} points, range {self.y_projection_full.min():.0f} to {self.y_projection_full.max():.0f}")

    def _update_plots(self):
        """Update plots with current slider ranges"""
        if self.x_projection_full is None or self.y_projection_full is None:
            return

        # Get current ranges from sliders
        x_min = self.x_min_slider.value()
        x_max = self.x_max_slider.value()
        y_min = self.y_min_slider.value()
        y_max = self.y_max_slider.value()

        # Ensure min < max
        if x_min >= x_max:
            x_max = x_min + 1
        if y_min >= y_max:
            y_max = y_min + 1

        # Update range labels
        self.x_range_label.setText(f"{x_min} - {x_max}")
        self.y_range_label.setText(f"{y_min} - {y_max}")

        # Clear previous plots
        self.ax_x.clear()
        self.ax_y.clear()

        # Plot X projection (horizontal profile) with limited range
        x_projection = self.x_projection_full[x_min:x_max+1]
        x_coords = np.arange(x_min, x_max+1)
        self.ax_x.plot(x_coords, x_projection, 'b-', linewidth=1)
        self.ax_x.set_xlabel('X Position (pixels)')
        self.ax_x.set_ylabel('Mean Pixel Value')
        self.ax_x.set_title(f'X Projection (Vertical Mean)\n{self.filename}')
        self.ax_x.grid(True, alpha=0.3)

        # Plot Y projection (vertical profile) with limited range
        y_projection = self.y_projection_full[y_min:y_max+1]
        y_coords = np.arange(y_min, y_max+1)
        self.ax_y.plot(y_coords, y_projection, 'r-', linewidth=1)
        self.ax_y.set_xlabel('Y Position (pixels)')
        self.ax_y.set_ylabel('Mean Pixel Value')
        self.ax_y.set_title('Y Projection (Horizontal Mean)')
        self.ax_y.grid(True, alpha=0.3)

        # Adjust layout and redraw
        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

    def _on_x_range_changed(self):
        """Handle X range slider changes"""
        self._update_plots()

    def _on_y_range_changed(self):
        """Handle Y range slider changes"""
        self._update_plots()

    def _on_apply(self):
        """Handle Apply button - save histogram settings to database"""
        if self.current_camera_id is None:
            print("No camera ID available - cannot save attributes")
            return

        try:
            from utils.db_manager import get_db_manager
            db = get_db_manager()

            # Get current slider values
            x_min = self.x_min_slider.value()
            x_max = self.x_max_slider.value()
            y_min = self.y_min_slider.value()
            y_max = self.y_max_slider.value()

            # Save to database (bits_per_pixel_actual is set elsewhere)
            db.update_camera_attributes(
                camera_id=self.current_camera_id,
                x_min=x_min,
                x_max=x_max,
                y_min=y_min,
                y_max=y_max,
                bits_per_pixel_actual=None  # Don't override, set elsewhere
            )

            print(f"Saved camera attributes: x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}")
            self.setWindowTitle(f"Axis Projections - Settings Saved")

            # Trigger reload of image with new crop settings
            if self.parent():
                from views.image_window import ImageWindow
                if isinstance(self.parent(), ImageWindow):
                    print("Reloading image with new crop settings...")
                    self.parent().reload_with_crop()

        except Exception as e:
            print(f"Error saving camera attributes: {e}")
            import traceback
            traceback.print_exc()
