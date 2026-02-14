"""
Application controller for managing state and coordinating between views.
Handles application logic and signal/slot connections.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QMessageBox
from typing import Optional, Dict, Any
from pathlib import Path
import numpy as np

from models.data_model import DataModel
from utils.plot_generator import get_plot_generator
from utils.image_loader import get_image_loader
from views.image_window import ImageWindow


class BackgroundImageLoader(QThread):
    """Background thread for loading images"""

    image_loaded = pyqtSignal(object, str)  # image_array, file_path
    error_occurred = pyqtSignal(str)        # error_message

    def __init__(self, file_path: str, camera_model: Optional[str] = None,
                 fast_preview: bool = False):
        """
        Initialize background loader.

        Args:
            file_path: Path to image file
            camera_model: Camera model for crop
            fast_preview: Use fast preview mode
        """
        super().__init__()
        self.file_path = file_path
        self.camera_model = camera_model
        self.fast_preview = fast_preview

    def run(self) -> None:
        """Load image in background"""
        try:
            loader = get_image_loader()
            image_array = loader.load_image(
                self.file_path,
                fast_preview=self.fast_preview,
                camera_model=self.camera_model
            )
            self.image_loaded.emit(image_array, self.file_path)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AppController(QObject):
    """Main application controller"""

    # Signals
    status_message = pyqtSignal(str)           # Status message
    error_occurred = pyqtSignal(str, str)      # title, message
    info_message = pyqtSignal(str, str)        # title, message

    def __init__(self, main_window):
        """
        Initialize application controller.

        Args:
            main_window: MainWindow instance
        """
        super().__init__()

        self.main_window = main_window
        self.data_model: Optional[DataModel] = None
        self.plot_generator = get_plot_generator()
        self.image_loader = get_image_loader()

        self.background_loader: Optional[BackgroundImageLoader] = None

        # Create image viewer window (reusable, persists across image loads)
        self.image_window = ImageWindow(main_window)

        # Initialize
        self._initialize_data_model()
        self._connect_signals()

    def _initialize_data_model(self) -> None:
        """Initialize data model"""
        try:
            self.data_model = DataModel()
            self.status_message.emit(
                f"Loaded {self.data_model.get_total_row_count()} records from database"
            )
        except Exception as e:
            self.error_occurred.emit(
                "Data Loading Error",
                f"Failed to load data from database:\n{str(e)}"
            )

    def _connect_signals(self) -> None:
        """Connect signals between components"""
        # Connect controller signals to main window
        self.status_message.connect(self.main_window.show_message)
        self.error_occurred.connect(self.main_window.show_error)
        self.info_message.connect(self.main_window.show_info)

        # Connect data browser signals
        data_browser = self.main_window.data_browser
        data_browser.row_selected.connect(self._on_data_row_selected)
        data_browser.data_filtered.connect(self._on_data_filtered)

        # Connect plot viewer signals
        self.main_window.plot_viewer.plot_updated.connect(
            lambda: self.status_message.emit("Plot updated")
        )

        # Connect image viewer signals
        self.main_window.image_viewer.image_loaded.connect(
            lambda path: self.status_message.emit(f"Image loaded: {Path(path).name}")
        )

    def _on_data_row_selected(self, row_index: int) -> None:
        """
        Handle data row selection.

        Args:
            row_index: Selected row index
        """
        try:
            row_data = self.main_window.data_browser.get_row_data(row_index)

            # Extract information
            camera = row_data.get('camera', 'Unknown')
            iso = row_data.get('iso', 'N/A')
            exposure_time = row_data.get('exposure_time', 'N/A')

            self.status_message.emit(
                f"Selected: {camera} | ISO {iso} | Exp: {exposure_time}s"
            )

            # If file_path is available, load image
            if 'file_path' in row_data and row_data['file_path']:
                file_path = row_data['file_path']
                if Path(file_path).exists():
                    self._load_image_for_row(file_path, camera)
                else:
                    # File not found, try to construct path
                    self.status_message.emit(
                        f"Image file not found: {file_path}"
                    )

        except Exception as e:
            self.error_occurred.emit(
                "Row Selection Error",
                f"Error processing selected row:\n{str(e)}"
            )

    def _load_image_for_row(self, file_path: str, camera_model: str) -> None:
        """
        Load image for selected row and open in popup window with raw data.

        Args:
            file_path: Path to image file
            camera_model: Camera model name
        """
        try:
            from PyQt6.QtGui import QPixmap, QImage
            import rawpy

            # Load raw data directly without color processing
            with rawpy.imread(str(file_path)) as raw:
                # Get raw pixel data (greyscale)
                raw_data = raw.raw_image.copy()

                # Apply camera-specific crop if available
                from sensor_camera import Sensor
                crop = Sensor.CAMERA_CROPS.get(camera_model)
                if crop is not None:
                    raw_data = raw_data[crop]

                # Calculate statistics
                mean_val = float(np.mean(raw_data))
                std_val = float(np.std(raw_data))
                ydim, xdim = raw_data.shape
                bit_depth = raw_data.dtype.itemsize * 8
                min_val = int(np.min(raw_data))
                max_val = int(np.max(raw_data))

                # Normalize to 8-bit for display
                if raw_data.dtype == np.uint16:
                    display_array = (raw_data.astype(np.float32) / 65535.0 * 255.0).astype(np.uint8)
                elif raw_data.dtype == np.uint8:
                    display_array = raw_data
                else:
                    # For other types, normalize to full range
                    min_val = np.min(raw_data)
                    max_val = np.max(raw_data)
                    if max_val > min_val:
                        display_array = ((raw_data.astype(np.float32) - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
                    else:
                        display_array = np.zeros_like(raw_data, dtype=np.uint8)

                # Convert to QImage (greyscale)
                bytes_per_line = xdim
                qimage = QImage(display_array.data, xdim, ydim, bytes_per_line, QImage.Format.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimage)

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

            # Calculate file hash and look up camera ID for histogram settings
            file_hash = None
            camera_id = None
            try:
                from utils.db_manager import get_db_manager
                db = get_db_manager()
                file_hash = db.calculate_file_hash(Path(file_path))
                camera_id = db.get_camera_id_by_file_hash(file_hash)
                print(f"Loaded image with camera_id={camera_id}")
            except Exception as e:
                print(f"Could not look up camera ID: {e}")

            # Open image window with loaded image and statistics
            self.image_window.load_image(
                pixmap, display_array, file_path,
                stats=stats, raw_data=raw_data,
                file_hash=file_hash, camera_id=camera_id
            )
            self.image_window.show()
            self.image_window.raise_()
            self.image_window.activateWindow()

        except Exception as e:
            self.error_occurred.emit(
                "Image Loading Error",
                f"Failed to load image:\n{str(e)}"
            )

    def _on_data_filtered(self) -> None:
        """Handle data filter change"""
        filtered_count = self.main_window.data_browser.data_model.get_row_count()
        total_count = self.main_window.data_browser.data_model.get_total_row_count()

        self.status_message.emit(
            f"Filtered: {filtered_count} of {total_count} records"
        )

        # Auto-regenerate plot with filtered data
        filtered_data = self.main_window.data_browser.data_model.get_data()
        self.main_window.plot_viewer.generate_plot_from_data(filtered_data)

    def load_image_background(self, file_path: str,
                            camera_model: Optional[str] = None,
                            fast_preview: bool = False) -> None:
        """
        Load image in background thread.

        Args:
            file_path: Path to image file
            camera_model: Camera model for crop
            fast_preview: Use fast preview mode
        """
        # Stop any existing background loading
        if self.background_loader and self.background_loader.isRunning():
            self.background_loader.quit()
            self.background_loader.wait()

        # Create and start new loader
        self.background_loader = BackgroundImageLoader(
            file_path, camera_model, fast_preview
        )
        self.background_loader.image_loaded.connect(self._on_background_image_loaded)
        self.background_loader.error_occurred.connect(self._on_background_error)
        self.background_loader.start()

        self.status_message.emit("Loading image...")

    def _on_background_image_loaded(self, image_array, file_path: str) -> None:
        """Handle background image loaded"""
        # Update image viewer with loaded image
        # (This would require modifying ImageViewer to accept numpy array directly)
        self.status_message.emit(f"Image loaded: {Path(file_path).name}")

    def _on_background_error(self, error_message: str) -> None:
        """Handle background loading error"""
        self.error_occurred.emit("Image Loading Error", error_message)

    def export_filtered_data(self, file_path: str) -> None:
        """
        Export filtered data to CSV.

        Args:
            file_path: Output file path
        """
        try:
            self.main_window.data_browser.export_data(file_path)
            self.info_message.emit(
                "Export Successful",
                f"Data exported to:\n{file_path}"
            )
        except Exception as e:
            self.error_occurred.emit(
                "Export Failed",
                f"Failed to export data:\n{str(e)}"
            )

    def clear_all_caches(self) -> None:
        """Clear all caches"""
        self.image_loader.clear_cache()
        self.status_message.emit("All caches cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.image_loader.get_cache_stats()

    def reload_data(self) -> None:
        """Reload all data from sources"""
        try:
            # Reload data model from database
            self.data_model = DataModel()
            self.main_window.data_browser.reload_data()

            # Reload plot generator
            self.plot_generator.reload_data()
            self.main_window.plot_viewer.refresh_data()

            self.status_message.emit("Data reloaded successfully")

        except Exception as e:
            self.error_occurred.emit(
                "Reload Failed",
                f"Failed to reload data:\n{str(e)}"
            )

    def shutdown(self) -> None:
        """Cleanup before shutdown"""
        # Stop any background threads
        if self.background_loader and self.background_loader.isRunning():
            self.background_loader.quit()
            self.background_loader.wait()

        # Clear caches to free memory
        self.clear_all_caches()
